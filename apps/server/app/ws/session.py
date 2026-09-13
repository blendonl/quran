import asyncio
import logging
import time

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.quran.corpus import QuranCorpus
from app.quran.ipa_database import IPADatabase
from app.matching.prefix_index import PrefixIndex
from app.config import settings
from app.transcription.engine_router import EngineRouter, EngineMode
from app.transcription.audio_buffer import AudioBuffer, BYTES_PER_SAMPLE
from app.matching.tracker import RecitationTracker, TrackerState
from app.matching.events import TrackerOutput
from app.matching.recitation_ledger import RecitationLedger
from app.ws.protocol import (
    PositionMessage,
    AyahStarted,
    AyahCompleted,
    SurahCompleted,
    BatchMessage,
    ErrorMessage,
    SessionReady,
    LetterStatusMessage,
    LetterStatusUpdate,
    TajweedStatusMessage,
    TajweedStatusUpdate,
    RecitationErrorMessage,
    RecitationErrorDetail as RecitationErrorDetailMsg,
    WordStatusMessage,
    WordStatusUpdateMsg,
    LocatingTimeout,
)

logger = logging.getLogger(__name__)

MIN_MUAALEM_AUDIO_S = 1.5
MIN_PER_WORD_AUDIO_S = 0.2


class RecitationSession:
    def __init__(
        self,
        ws: WebSocket,
        corpus: QuranCorpus,
        engine_router: EngineRouter,
        prefix_index: PrefixIndex,
        ipa_database: IPADatabase | None = None,
        noise_filter=None,
    ):
        self.ws = ws
        self.corpus = corpus
        self.engine_router = engine_router
        self.prefix_index = prefix_index
        self.ipa_database = ipa_database
        self.noise_filter = noise_filter
        self.audio_buffer = AudioBuffer()
        self.tracker = RecitationTracker(corpus, prefix_index, ipa_database)
        self.ledger = RecitationLedger()
        self.active = False
        self._audio_queue: asyncio.Queue = asyncio.Queue(maxsize=4)
        self._process_task: asyncio.Task | None = None
        self._last_inference_duration: float = 0.25
        self._dropped_frames: int = 0
        self._encoding: str = "pcm_s16le"
        self._opus_decoder = None
        self._word_start_samples: dict[int, int] = {}
        self._muaalem_graded_words: set[int] = set()
        self._pending_muaalem: asyncio.Task | None = None
        self._ws_lock = asyncio.Lock()
        self._last_word_index: int = -1

    async def start(
        self,
        sample_rate: int = 16000,
        surah_id: int | None = None,
        ayah_number: int | None = None,
        encoding: str = "pcm_s16le",
    ):
        self._encoding = encoding
        if encoding == "opus":
            from app.audio.opus_decoder import OpusDecoder

            self._opus_decoder = OpusDecoder(sample_rate=sample_rate)
        else:
            self._opus_decoder = None

        self.audio_buffer = AudioBuffer(sample_rate=sample_rate)
        self.ledger.reset()
        self._word_start_samples = {0: 0}
        self._muaalem_graded_words = set()
        self._pending_muaalem = None
        self._last_word_index = -1
        if surah_id is not None and ayah_number is not None:
            output = self.tracker.set_position(surah_id, ayah_number)
            await self.engine_router.ensure_loaded()
            self.active = True
            self._audio_queue = asyncio.Queue(maxsize=4)
            self._process_task = asyncio.create_task(self._process_loop())
            await self.ws.send_json(SessionReady().model_dump())
            await self._send_tracker_output(output)
        else:
            self.tracker.reset()
            await self.engine_router.ensure_loaded()
            self.active = True
            self._audio_queue = asyncio.Queue(maxsize=4)
            self._process_task = asyncio.create_task(self._process_loop())
            await self.ws.send_json(SessionReady().model_dump())

    async def stop(self):
        self.active = False
        if self._pending_muaalem and not self._pending_muaalem.done():
            self._pending_muaalem.cancel()
            try:
                await self._pending_muaalem
            except (asyncio.CancelledError, Exception):
                pass
            self._pending_muaalem = None
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
            self._process_task = None
        self.audio_buffer.reset()

    async def process_audio(self, audio_data: bytes):
        if not self.active:
            return

        if self._opus_decoder is not None:
            try:
                pcm_data = self._opus_decoder.decode(audio_data)
            except Exception as e:
                logger.warning("Opus decode error: %s", e)
                return
        else:
            pcm_data = audio_data

        snapshot = self.audio_buffer.add_audio(pcm_data)
        if snapshot is None:
            return

        if self._audio_queue.full():
            try:
                self._audio_queue.get_nowait()
                self._dropped_frames += 1
                if self._dropped_frames % 10 == 1:
                    logger.warning("Audio queue overflow: %d frames dropped", self._dropped_frames)
            except asyncio.QueueEmpty:
                pass
        try:
            self._audio_queue.put_nowait(snapshot)
        except asyncio.QueueFull:
            pass

    def _get_engine_mode(self) -> EngineMode:
        if self.tracker.state == TrackerState.LOCATING:
            return EngineMode.CTC_TEXT
        if settings.phoneme_engine_type == "muaalem":
            if settings.ctc_engine_type not in ("nemo", "whisper", "tarteel"):
                return EngineMode.FORCED_ALIGN
            return EngineMode.CTC_TEXT
        if self.tracker.has_phoneme_tracker:
            return EngineMode.PHONEME
        return EngineMode.CTC_TEXT

    async def _process_loop(self):
        while self.active:
            try:
                snapshot = await self._audio_queue.get()
            except asyncio.CancelledError:
                break

            start_time = time.monotonic()
            try:
                mode = self._get_engine_mode()

                if mode == EngineMode.FORCED_ALIGN:
                    self.audio_buffer.trim_on_silence = False
                    await self._process_forced_align(snapshot)
                    continue

                if self.tracker.state == TrackerState.LOCATING:
                    self.audio_buffer.trim_on_silence = False
                    if self.audio_buffer.silence_detected:
                        self.tracker.reset_locate_votes()
                        self.audio_buffer.silence_detected = False
                else:
                    self.audio_buffer.trim_on_silence = True

                if mode == EngineMode.CTC_TEXT and self.tracker.state == TrackerState.LOCATING:
                    min_locate_samples = int(settings.audio_min_locate_s * self.audio_buffer.sample_rate)
                    if len(snapshot) < min_locate_samples:
                        continue
                    max_locate_samples = int(settings.audio_max_locate_snapshot_s * self.audio_buffer.sample_rate)
                    if len(snapshot) > max_locate_samples:
                        snapshot = snapshot[-max_locate_samples:]

                if self.noise_filter is not None:
                    snapshot = await self.noise_filter.filter(snapshot)

                use_beam = mode != EngineMode.CTC_TEXT
                if mode == EngineMode.CTC_TEXT and self.tracker.state != TrackerState.LOCATING:
                    max_samples = int(settings.audio_max_tracking_snapshot_s * self.audio_buffer.sample_rate)
                    if len(snapshot) > max_samples:
                        snapshot = snapshot[-max_samples:]

                engine_output = await self.engine_router.transcribe(
                    snapshot, mode, use_beam=use_beam,
                )

                if not engine_output:
                    continue

                pre_process_ayah = self.tracker.current_ayah  # Save before CTC may transition

                if engine_output.ctc_result:
                    output = self.tracker.process_ctc_result(engine_output.ctc_result)
                elif engine_output.phoneme_result:
                    output = self.tracker.process_phoneme_result(engine_output.phoneme_result)
                else:
                    continue

                filtered = self.ledger.apply(output)
                await self._send_tracker_output(filtered)

                for pos in output.positions:
                    current_word = pos.word_index
                    if current_word not in self._word_start_samples:
                        self._word_start_samples[current_word] = self.audio_buffer.total_samples
                    if current_word > self._last_word_index and self._last_word_index >= 0:
                        for completed in range(self._last_word_index, current_word):
                            self._schedule_per_word_muaalem(completed, pre_process_ayah)
                    self._last_word_index = current_word

                if self.audio_buffer.silence_detected and self.tracker.state == TrackerState.TRACKING:
                    deferred = self.ledger.flush_deferred()
                    if deferred.tajweed_statuses or deferred.recitation_errors:
                        await self._send_tracker_output(deferred)
                    self.audio_buffer.silence_detected = False

                if output.surah_completed:
                    self.active = False
                    break
                if any(e.event_type == "ayah.completed" for e in output.ayah_events):
                    if pre_process_ayah:
                        await self._run_muaalem_on_completion(pre_process_ayah)
                    self.ledger.reset()
                    self.audio_buffer.reset()
                    self.audio_buffer.set_recovery_mode()
                    self._word_start_samples = {0: 0}
                    self._muaalem_graded_words = set()
                    self._last_word_index = -1
                    if self._pending_muaalem and not self._pending_muaalem.done():
                        self._pending_muaalem.cancel()
                        self._pending_muaalem = None
                    while not self._audio_queue.empty():
                        try:
                            self._audio_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
            except WebSocketDisconnect:
                self.active = False
                break
            except Exception as e:
                logger.exception("Error processing audio snapshot")
                try:
                    await self.ws.send_json(
                        ErrorMessage(message=f"Processing error: {e}").model_dump()
                    )
                except (WebSocketDisconnect, RuntimeError):
                    self.active = False
                    break
            finally:
                elapsed = time.monotonic() - start_time
                self._last_inference_duration = elapsed
                new_interval = max(0.15, min(elapsed * 1.1, 0.5))
                self.audio_buffer.emit_interval_bytes = int(
                    new_interval * self.audio_buffer.sample_rate * BYTES_PER_SAMPLE
                )
                logger.debug(
                    "Process loop: elapsed=%.3fs interval=%.3fs queue=%d",
                    elapsed, new_interval, self._audio_queue.qsize(),
                )

    async def _process_forced_align(self, snapshot):
        ayah = self.tracker.current_ayah
        if not ayah:
            return

        full_audio = self.audio_buffer.get_full_audio()
        if full_audio is None:
            return

        min_samples = int(settings.forced_align_min_audio_s * self.audio_buffer.sample_rate)
        if len(full_audio) < min_samples:
            return

        word_offset = self.tracker._confirmed_word_index + 1
        remaining_words = ayah.normalized_words[word_offset:]
        if not remaining_words:
            return
        remaining_text = "".join(remaining_words)

        align_result = await self.engine_router.forced_align(
            full_audio, remaining_text, remaining_words,
        )
        if not align_result:
            return

        for wb in align_result.word_boundaries:
            wb.word_index += word_offset

        scores = [f"{wb.word_index}:{wb.score:.2f}" for wb in align_result.word_boundaries]
        logger.info(
            "FORCED_ALIGN %d:%d frames=%d words=[%s] confirmed=%d offset=%d",
            ayah.surah_id, ayah.ayah_number,
            align_result.total_frames,
            " ".join(scores),
            self.tracker._confirmed_word_index,
            word_offset,
        )

        output = self.tracker.process_forced_align_result(align_result)

        ayah_completed = any(e.event_type == "ayah.completed" for e in output.ayah_events)
        if ayah_completed:
            await self._run_muaalem_on_completion(ayah)
            self.tracker._transition_to_next(output)

        await self._send_tracker_output(output)

        if ayah_completed:
            self.audio_buffer.reset()
            self.audio_buffer.set_recovery_mode()
            while not self._audio_queue.empty():
                try:
                    self._audio_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

        if output.surah_completed:
            self.active = False

    def _schedule_per_word_muaalem(self, completed_word: int, ayah):
        if ayah is None:
            return
        if completed_word in self._muaalem_graded_words:
            return
        if self._pending_muaalem and not self._pending_muaalem.done():
            return

        start_sample = self._word_start_samples.get(completed_word, 0)
        end_sample = self.audio_buffer.total_samples
        duration_s = (end_sample - start_sample) / self.audio_buffer.sample_rate
        if duration_s < MIN_PER_WORD_AUDIO_S:
            return

        audio = self.audio_buffer.get_audio_range(start_sample, end_sample)
        if audio is None:
            return

        self._pending_muaalem = asyncio.create_task(
            self._run_per_word_muaalem(ayah, completed_word, audio)
        )

    async def _run_per_word_muaalem(self, ayah, completed_word: int, audio):
        if not self.active:
            return
        try:
            if not await self.engine_router.ensure_muaalem_loaded():
                return

            muaalem_result = await self.engine_router.muaalem_engine.transcribe(
                audio, ayah.surah_id, ayah.ayah_number,
            )
            if not muaalem_result or not self.active:
                return

            output = self.tracker.process_word_muaalem_result(
                muaalem_result, ayah, target_word=completed_word,
            )
            self._muaalem_graded_words.add(completed_word)
            filtered = self.ledger.apply(output)
            await self._send_tracker_output(filtered)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Per-word Muaalem failed for word %d", completed_word)

    async def _run_muaalem_on_completion(self, ayah):
        if self._pending_muaalem and not self._pending_muaalem.done():
            try:
                await asyncio.wait_for(self._pending_muaalem, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                pass
            self._pending_muaalem = None

        full_audio = self.audio_buffer.get_full_audio()
        if full_audio is None:
            return

        min_muaalem_samples = int(MIN_MUAALEM_AUDIO_S * self.audio_buffer.sample_rate)
        if len(full_audio) < min_muaalem_samples:
            logger.warning(
                "Muaalem skipped: audio too short (%.2fs < %.2fs) for %d:%d",
                len(full_audio) / self.audio_buffer.sample_rate,
                MIN_MUAALEM_AUDIO_S,
                ayah.surah_id, ayah.ayah_number,
            )
            return

        if not await self.engine_router.ensure_muaalem_loaded():
            return

        total_words = len(ayah.normalized_words)
        ungraded = [i for i in range(total_words) if i not in self._muaalem_graded_words]
        if not ungraded:
            return

        muaalem_result = await self.engine_router.muaalem_engine.transcribe(
            full_audio, ayah.surah_id, ayah.ayah_number,
        )
        if not muaalem_result:
            return

        for word_idx in ungraded:
            output = self.tracker.process_word_muaalem_result(
                muaalem_result, ayah, target_word=word_idx,
            )
            self._muaalem_graded_words.add(word_idx)
            filtered = self.ledger.apply(output)
            await self._send_tracker_output(filtered)

    async def _send_tracker_output(self, output: TrackerOutput):
        async with self._ws_lock:
            await self._send_tracker_output_locked(output)

    async def _send_tracker_output_locked(self, output: TrackerOutput):
        messages: list[dict] = []

        for event in output.ayah_events:
            if event.event_type == "ayah.started":
                messages.append(AyahStarted(
                    surah_id=event.surah_id,
                    ayah_number=event.ayah_number,
                    text=event.text,
                ).model_dump())
                logger.debug("WS send ayah.started: %d:%d", event.surah_id, event.ayah_number)
            elif event.event_type == "ayah.completed":
                messages.append(AyahCompleted(
                    surah_id=event.surah_id,
                    ayah_number=event.ayah_number,
                ).model_dump())
                logger.debug("WS send ayah.completed: %d:%d", event.surah_id, event.ayah_number)

        for pos in output.positions:
            messages.append(PositionMessage(
                surah_id=pos.surah_id,
                ayah_number=pos.ayah_number,
                word_index=pos.word_index,
                confidence=pos.confidence,
            ).model_dump())
            logger.debug("WS send position: %d:%d word=%d conf=%.2f", pos.surah_id, pos.ayah_number, pos.word_index, pos.confidence)

        for letter_event in output.letter_statuses:
            messages.append(LetterStatusMessage(
                surah_id=letter_event.surah_id,
                ayah_number=letter_event.ayah_number,
                updates=[
                    LetterStatusUpdate(
                        word_index=u.word_index,
                        letter_index=u.letter_index,
                        status=u.status.value,
                    )
                    for u in letter_event.updates
                ],
                confidence=letter_event.confidence,
            ).model_dump())
            correct = sum(1 for u in letter_event.updates if u.status.value == "CORRECT")
            total = len(letter_event.updates)
            logger.debug(
                "WS send letter.status: %d:%d letters=%d correct=%d/%d conf=%.2f",
                letter_event.surah_id, letter_event.ayah_number,
                total, correct, total, letter_event.confidence,
            )

        for tajweed_event in output.tajweed_statuses:
            messages.append(TajweedStatusMessage(
                surah_id=tajweed_event.surah_id,
                ayah_number=tajweed_event.ayah_number,
                updates=[
                    TajweedStatusUpdate(
                        word_index=u.word_index,
                        letter_index=u.letter_index,
                        rule=u.rule,
                        grade=u.grade,
                    )
                    for u in tajweed_event.updates
                ],
            ).model_dump())
            logger.debug(
                "WS send tajweed.status: %d:%d rules=%d",
                tajweed_event.surah_id, tajweed_event.ayah_number,
                len(tajweed_event.updates),
            )

        for error_event in output.recitation_errors:
            messages.append(RecitationErrorMessage(
                surah_id=error_event.surah_id,
                ayah_number=error_event.ayah_number,
                errors=[
                    RecitationErrorDetailMsg(
                        error_type=e.error_type,
                        speech_error_type=e.speech_error_type,
                        expected_phoneme=e.expected_phoneme,
                        predicted_phoneme=e.predicted_phoneme,
                        uthmani_start=e.uthmani_start,
                        uthmani_end=e.uthmani_end,
                        tajweed_rule=e.tajweed_rule,
                        expected_len=e.expected_len,
                        predicted_len=e.predicted_len,
                    )
                    for e in error_event.errors
                ],
            ).model_dump())
            logger.debug(
                "WS send recitation.error: %d:%d errors=%d",
                error_event.surah_id, error_event.ayah_number,
                len(error_event.errors),
            )

        for word_event in output.word_statuses:
            messages.append(WordStatusMessage(
                surah_id=word_event.surah_id,
                ayah_number=word_event.ayah_number,
                updates=[
                    WordStatusUpdateMsg(
                        word_index=u.word_index,
                        status=u.status,
                        confidence=u.confidence,
                        tajweed_grade=u.tajweed_grade,
                    )
                    for u in word_event.updates
                ],
            ).model_dump())
            logger.debug(
                "WS send word.status: %d:%d words=%d",
                word_event.surah_id, word_event.ayah_number,
                len(word_event.updates),
            )

        for sc in output.surah_completed:
            messages.append(SurahCompleted(
                surah_id=sc.surah_id,
                ayah_number=sc.ayah_number,
                next_surah_id=sc.next_surah_id,
            ).model_dump())
            logger.debug("WS send surah.completed: %d next=%s", sc.surah_id, sc.next_surah_id)

        if output.locating_timeout:
            messages.append(LocatingTimeout().model_dump())
            logger.info("WS send locating.timeout")

        if messages:
            types = [m.get("type", "?") for m in messages]
            logger.info("WS send: %s", types)
            if len(messages) == 1:
                await self.ws.send_json(messages[0])
            else:
                await self.ws.send_json(BatchMessage(messages=messages).model_dump())
