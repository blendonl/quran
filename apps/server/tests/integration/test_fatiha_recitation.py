import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pytest

from app.config import settings
from app.matching.events import (
    LetterStatus,
    TrackerOutput,
)
from app.matching.tracker import RecitationTracker, TrackerState
from app.transcription.audio_buffer import AudioBuffer
from app.transcription.engine_router import EngineMode, EngineRouter

from tests.integration.conftest import _ensure_reciter_audio, load_pcm_as_int16

logger = logging.getLogger(__name__)

CHUNK_DURATION_S = 0.25
SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2
CHUNK_BYTES = int(CHUNK_DURATION_S * SAMPLE_RATE * BYTES_PER_SAMPLE)

MIN_LETTER_ACCURACY = 0.40
MAX_INCORRECT_RATIO = 0.25


@dataclass
class AyahScore:
    ayah_number: int
    started: bool = False
    completed: bool = False
    letter_statuses: dict[tuple[int, int], LetterStatus] = field(default_factory=dict)
    max_word_index: int = 0
    error_count: int = 0

    @property
    def total_letters(self) -> int:
        return len(self.letter_statuses)

    @property
    def correct_count(self) -> int:
        return sum(1 for s in self.letter_statuses.values() if s == LetterStatus.CORRECT)

    @property
    def incorrect_count(self) -> int:
        return sum(1 for s in self.letter_statuses.values() if s == LetterStatus.INCORRECT)

    @property
    def accuracy(self) -> float:
        if self.total_letters == 0:
            return 0.0
        return self.correct_count / self.total_letters

    @property
    def incorrect_ratio(self) -> float:
        if self.total_letters == 0:
            return 0.0
        return self.incorrect_count / self.total_letters


@dataclass
class SurahScore:
    ayahs: dict[int, AyahScore] = field(default_factory=dict)
    surah_completed: bool = False

    def get_or_create(self, ayah_number: int) -> AyahScore:
        if ayah_number not in self.ayahs:
            self.ayahs[ayah_number] = AyahScore(ayah_number=ayah_number)
        return self.ayahs[ayah_number]


def _accumulate_output(score: SurahScore, output: TrackerOutput):
    for event in output.ayah_events:
        ayah_score = score.get_or_create(event.ayah_number)
        if event.event_type == "ayah.started":
            ayah_score.started = True
        elif event.event_type == "ayah.completed":
            ayah_score.completed = True

    for letter_event in output.letter_statuses:
        ayah_score = score.get_or_create(letter_event.ayah_number)
        for update in letter_event.updates:
            key = (update.word_index, update.letter_index)
            ayah_score.letter_statuses[key] = update.status

    for pos in output.positions:
        ayah_score = score.get_or_create(pos.ayah_number)
        ayah_score.max_word_index = max(ayah_score.max_word_index, pos.word_index)

    for error_event in output.recitation_errors:
        ayah_score = score.get_or_create(error_event.ayah_number)
        ayah_score.error_count += len(error_event.errors)

    for sc in output.surah_completed:
        score.surah_completed = True


def _get_engine_mode(tracker: RecitationTracker) -> EngineMode:
    if tracker.state == TrackerState.LOCATING:
        return EngineMode.CTC_TEXT
    if settings.phoneme_engine_type == "muaalem":
        return EngineMode.MUAALEM
    if tracker.has_phoneme_tracker:
        return EngineMode.PHONEME
    return EngineMode.CTC_TEXT


async def _run_recitation(
    reciter: str,
    pcm_files: list[Path],
    engine_router: EngineRouter,
    corpus,
    prefix_index,
    ipa_database,
) -> SurahScore:
    logger.info("Loading engine models...")
    await engine_router.ensure_loaded()
    logger.info("Engine models loaded")

    tracker = RecitationTracker(corpus, prefix_index, ipa_database)
    audio_buffer = AudioBuffer(sample_rate=SAMPLE_RATE)

    output = tracker.set_position(1, 1)
    score = SurahScore()
    _accumulate_output(score, output)

    for file_idx, pcm_path in enumerate(pcm_files):
        logger.info("Processing file %d/%d: %s", file_idx + 1, len(pcm_files), pcm_path.name)
        pcm_int16 = load_pcm_as_int16(pcm_path)
        pcm_bytes = pcm_int16.tobytes()

        for offset in range(0, len(pcm_bytes), CHUNK_BYTES):
            chunk = pcm_bytes[offset:offset + CHUNK_BYTES]
            if len(chunk) == 0:
                break

            snapshot = audio_buffer.add_audio(chunk)
            if snapshot is None:
                continue

            mode = _get_engine_mode(tracker)

            surah_id = None
            ayah_number = None
            if mode == EngineMode.MUAALEM and tracker.current_ayah:
                surah_id = tracker.current_ayah.surah_id
                ayah_number = tracker.current_ayah.ayah_number

            engine_output = await engine_router.transcribe(
                snapshot, mode, surah_id=surah_id, ayah_number=ayah_number
            )

            if not engine_output:
                continue

            if engine_output.ctc_result:
                output = tracker.process_ctc_result(engine_output.ctc_result)
            elif engine_output.phoneme_result:
                output = tracker.process_phoneme_result(engine_output.phoneme_result)
            elif engine_output.muaalem_result:
                output = tracker.process_muaalem_result(engine_output.muaalem_result)
            else:
                continue

            _accumulate_output(score, output)

            if output.surah_completed:
                return score

            if any(e.event_type == "ayah.completed" for e in output.ayah_events):
                audio_buffer.reset()
                break

    return score


def _log_score(reciter: str, score: SurahScore):
    logger.info("RECITER: %s", reciter)
    for ayah_num in sorted(score.ayahs.keys()):
        a = score.ayahs[ayah_num]
        status = "PASS" if a.completed and a.accuracy >= MIN_LETTER_ACCURACY else "FAIL"
        logger.info(
            "  Ayah %d [%s]: started=%s completed=%s letters=%d correct=%d (%.0f%%) "
            "incorrect=%d (%.0f%%) errors=%d",
            ayah_num, status,
            a.started, a.completed,
            a.total_letters, a.correct_count, a.accuracy * 100,
            a.incorrect_count, a.incorrect_ratio * 100,
            a.error_count,
        )
    logger.info("  Surah completed: %s", score.surah_completed)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize("reciter", [
    "Alafasy_128kbps",
    "Abdul_Basit_Murattal_64kbps",
    "Husary_128kbps",
])
async def test_fatiha_recitation(
    reciter,
    audio_fixtures,
    engine_router,
    corpus,
    prefix_index,
    ipa_database,
):
    if reciter not in audio_fixtures:
        audio_fixtures[reciter] = _ensure_reciter_audio(reciter)
    pcm_files = audio_fixtures[reciter]

    score = await _run_recitation(
        reciter, pcm_files, engine_router, corpus, prefix_index, ipa_database,
    )

    _log_score(reciter, score)

    for ayah_num in range(1, 8):
        ayah_score = score.ayahs.get(ayah_num)
        assert ayah_score is not None, f"Ayah {ayah_num} never appeared"
        assert ayah_score.started, f"Ayah {ayah_num} never started"
        assert ayah_score.completed, f"Ayah {ayah_num} never completed"

    completed_order = [
        n for n in sorted(score.ayahs.keys())
        if score.ayahs[n].completed
    ]
    assert completed_order == list(range(1, 8)), (
        f"Ayahs did not complete in order: {completed_order}"
    )

    for ayah_num in range(1, 8):
        a = score.ayahs[ayah_num]
        assert a.accuracy >= MIN_LETTER_ACCURACY, (
            f"Ayah {ayah_num} accuracy {a.accuracy:.0%} < {MIN_LETTER_ACCURACY:.0%} "
            f"(correct={a.correct_count}/{a.total_letters})"
        )
        assert a.incorrect_ratio <= MAX_INCORRECT_RATIO, (
            f"Ayah {ayah_num} incorrect ratio {a.incorrect_ratio:.0%} > {MAX_INCORRECT_RATIO:.0%} "
            f"(incorrect={a.incorrect_count}/{a.total_letters})"
        )

    assert score.surah_completed, "surah.completed event never fired"
