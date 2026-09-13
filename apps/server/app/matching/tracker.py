import bisect
import logging
from collections import defaultdict
from enum import Enum

from app.config import settings
from app.quran.corpus import QuranCorpus, QuranAyah
from app.quran.normalizer import normalize, TASHKEEL_PATTERN

try:
    from quran_transcript.phonetics.error_explainer import explain_error as _explain_error
except ImportError:
    _explain_error = None
from app.quran.ipa_database import IPADatabase
from app.transcription.ctc_result import CTCResult
from app.transcription.phoneme_result import PhonemeResult
from app.transcription.muaalem_engine import SIFA_ATTRS
from app.transcription.muaalem_result import MuaalemResult
from app.matching.phonetic import phonetic_match, to_phonetic
from app.matching.prefix_index import PrefixIndex, MatchCandidate
from app.matching.muqattaat import is_muqattaat
from app.matching.phoneme_tracker import PhonemeTracker
from app.transcription.forced_align import ForcedAlignResult
from app.matching.events import (
    LetterStatus,
    LetterUpdate,
    LetterStatusEvent,
    PositionEvent,
    AyahEvent,
    MistakeEvent,
    SurahCompletedEvent,
    TajweedUpdate,
    TajweedStatusEvent,
    RecitationErrorDetail,
    RecitationErrorEvent,
    WordStatusUpdate,
    WordStatusEvent,
    TrackerOutput,
)

logger = logging.getLogger(__name__)

MIN_TRANSCRIPTION_LENGTH = 7
MIN_LOCATE_CHARS = 3
MIN_LOCATE_UNIQUE_LEN = 7
MIN_LOCATE_MATCH_COUNT = 8
MIN_LOCATE_STRONG_MATCH = 12
MAX_LOCATE_STRONG_CANDIDATES = 3
LOCATE_VOTE_THRESHOLD = 3
MAX_VOTE_CANDIDATES = 50
TRACK_THRESHOLD = settings.matching_track_threshold
MUAALEM_CORRECT_THRESHOLD = settings.matching_muaalem_correct_threshold
AYAH_COMPLETE_RATIO = settings.matching_ayah_complete_ratio
MAX_CHAR_SKIP = 3
MAX_POSITION_JUMP = 3
NEXT_AYAH_CHECK_RATIO = 0.5
REPEAT_CHECK_RATIO = 0.5
NEXT_AYAH_PREFIX_LEN = 20
FORCED_ALIGN_WORD_THRESHOLD = settings.forced_align_word_threshold
MISTAKE_THRESHOLD = settings.matching_mistake_threshold
CONSECUTIVE_FAILURES_BEFORE_MISTAKE = settings.matching_consecutive_failures
MAX_SEARCH_RANGE = 30
TRANSITION_GRACE_CYCLES = settings.matching_transition_grace_cycles


class TrackerState(Enum):
    LOCATING = "locating"
    TRACKING = "tracking"


class RecitationTracker:
    def __init__(
        self,
        corpus: QuranCorpus,
        prefix_index: PrefixIndex,
        ipa_database: IPADatabase | None = None,
    ):
        self.corpus = corpus
        self.prefix_index = prefix_index
        self.ipa_database = ipa_database
        self.state = TrackerState.LOCATING
        self.current_ayah: QuranAyah | None = None
        self.current_word_index: int = 0
        self.matched_char_pos: int = 0
        self._candidates: list[MatchCandidate] = []
        self._prev_phonetic_query: str = ""
        self._need_advance_to_complete: bool = False
        self._consecutive_failures: int = 0
        self._status_votes: dict[tuple[int, int], list[LetterStatus]] = defaultdict(list)
        self._recent_transcriptions: list[str] = []
        self._transition_grace: int = 0
        self._phoneme_tracker: PhonemeTracker | None = None
        self._muaalem_complete_count: int = 0
        self._muaalem_last_word_count: int = 0
        self._muaalem_frames_tracked: int = 0
        self._last_error_keys: set[tuple] = set()
        self._locate_votes: dict[tuple[int, int], int] = {}
        self._locate_attempts: int = 0
        self._phoneme_complete_count: int = 0
        self._ctc_complete_count: int = 0
        self._confirmed_word_index: int = -1

    def set_position(self, surah_id: int, ayah_number: int) -> TrackerOutput:
        output = TrackerOutput()
        ayah = self.corpus.get_ayah(surah_id, ayah_number)
        if not ayah:
            return output

        self.current_ayah = ayah
        self.matched_char_pos = 0
        self.current_word_index = 0
        self.state = TrackerState.TRACKING
        self._need_advance_to_complete = False
        self._consecutive_failures = 0
        self._status_votes.clear()
        self._recent_transcriptions.clear()
        self._transition_grace = TRANSITION_GRACE_CYCLES
        self._muaalem_complete_count = 0
        self._muaalem_last_word_count = 0
        self._muaalem_frames_tracked = 0
        self._last_error_keys = set()
        self._confirmed_word_index = -1
        self._init_phoneme_tracker(ayah)

        output.ayah_events.append(AyahEvent(
            event_type="ayah.started",
            surah_id=ayah.surah_id,
            ayah_number=ayah.ayah_number,
            text=ayah.text,
        ))
        return output

    def process_ctc_result(self, ctc_result: CTCResult) -> TrackerOutput:
        normalized = normalize(ctc_result.characters)
        text = normalized.replace(" ", "")

        if self.state == TrackerState.LOCATING:
            logger.info("LOCATING CTC: '%s' (conf=%.2f)", normalized, ctc_result.confidence)
            words = normalized.split()
            return self._handle_locating(text, words, ctc_result.confidence)

        if len(text) < MIN_TRANSCRIPTION_LENGTH:
            return TrackerOutput()
        return self._handle_tracking(text, ctc_result.confidence)

    def process_phoneme_result(self, phoneme_result: PhonemeResult) -> TrackerOutput:
        output = TrackerOutput()
        if self.state != TrackerState.TRACKING:
            return output

        ayah = self.current_ayah
        if not ayah or not self._phoneme_tracker:
            return output

        if self._transition_grace > 0:
            self._transition_grace -= 1
            return output

        avg_confidence = sum(phoneme_result.confidences) / max(len(phoneme_result.confidences), 1)
        old_word = self._phoneme_tracker.word_index_at_position()

        track_result = self._phoneme_tracker.process(
            phoneme_result.phonemes,
            ayah.surah_id,
            ayah.ayah_number,
            avg_confidence,
        )

        if track_result.letter_event:
            output.letter_statuses.append(track_result.letter_event)
        if track_result.tajweed_event:
            output.tajweed_statuses.append(track_result.tajweed_event)

        new_word = self._phoneme_tracker.word_index_at_position()
        if new_word > old_word:
            self.current_word_index = new_word
            output.positions.append(PositionEvent(
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
                word_index=new_word,
                confidence=avg_confidence,
            ))

        if self._phoneme_tracker.is_complete:
            self._phoneme_complete_count += 1
            if self._phoneme_complete_count >= 2:
                logger.info("PHONEME COMPLETED: %d:%d", ayah.surah_id, ayah.ayah_number)
                output.ayah_events.append(AyahEvent(
                    event_type="ayah.completed",
                    surah_id=ayah.surah_id,
                    ayah_number=ayah.ayah_number,
                ))
                self._phoneme_complete_count = 0
                self._transition_to_next(output)
        else:
            self._phoneme_complete_count = 0

        return output

    def process_muaalem_result(self, result: MuaalemResult) -> TrackerOutput:
        output = TrackerOutput()
        if self.state != TrackerState.TRACKING:
            return output

        ayah = self.current_ayah
        if not ayah:
            return output

        if self._transition_grace > 0:
            self._transition_grace -= 1
            return output

        self._muaalem_frames_tracked += 1

        logger.debug(
            "MUAALEM frame %d: ayah=%d:%d word_index=%d grace=%d",
            self._muaalem_frames_tracked, ayah.surah_id, ayah.ayah_number,
            self.current_word_index, self._transition_grace,
        )

        avg_confidence = sum(result.confidences) / max(len(result.confidences), 1)

        predicted_len = len(result.phonemes_text.replace("[PAD]", "").strip())
        ref_len = max(result.ref_phonemes_len, 1)
        coverage_ratio = min(1.0, predicted_len / ref_len)

        letter_updates = []
        tajweed_updates = []
        error_event = None

        if result.word_phoneme_map and ayah.uthmani_char_map:
            old_word = self.current_word_index
            max_confident_word = old_word

            for word_entry in result.word_phoneme_map:
                wi = word_entry["word_index"]
                sifat_start = word_entry["sifat_start"]
                sifat_end = word_entry["sifat_end"]
                word_confs = result.confidences[sifat_start:sifat_end]
                word_avg = sum(word_confs) / max(len(word_confs), 1) if word_confs else 0.0
                if word_avg >= TRACK_THRESHOLD and wi > max_confident_word:
                    max_confident_word = wi

            mapped_words = {w["word_index"]: result.confidences[w["sifat_start"]:w["sifat_end"]] for w in result.word_phoneme_map}
            logger.debug(
                "MUAALEM word_map: words=%s max_confident=%d",
                {wi: f"{sum(c)/max(len(c),1):.2f}" for wi, c in mapped_words.items()},
                max_confident_word,
            )

            error_event = self._extract_recitation_errors(result, ayah, max_confident_word)
            error_affected: set[tuple[int, int]] = set()
            if error_event:
                consonant_errors = [e for e in error_event.errors if e.error_type == "normal"]
                error_affected = self._error_affected_letters(
                    result.uthmani_text, consonant_errors, pos_to_wl=ayah.pos_to_wl or None,
                )

            for word_entry in result.word_phoneme_map:
                wi = word_entry["word_index"]
                sifat_start = word_entry["sifat_start"]
                sifat_end = word_entry["sifat_end"]

                word_confs = result.confidences[sifat_start:sifat_end]
                word_avg = sum(word_confs) / max(len(word_confs), 1) if word_confs else 0.0

                if word_avg < TRACK_THRESHOLD:
                    continue

                word_letters = ayah.word_to_letters.get(wi) if ayah.word_to_letters else None
                if word_letters:
                    for cw, cl in word_letters:
                        if (cw, cl) in error_affected:
                            status = LetterStatus.INCORRECT
                        else:
                            status = LetterStatus.CORRECT if word_avg >= MUAALEM_CORRECT_THRESHOLD else LetterStatus.NOT_SURE
                        letter_updates.append(LetterUpdate(word_index=cw, letter_index=cl, status=status))
                else:
                    for cw, cl in ayah.uthmani_char_map:
                        if cw != wi:
                            continue
                        if (cw, cl) in error_affected:
                            status = LetterStatus.INCORRECT
                        else:
                            status = LetterStatus.CORRECT if word_avg >= MUAALEM_CORRECT_THRESHOLD else LetterStatus.NOT_SURE
                        letter_updates.append(LetterUpdate(word_index=cw, letter_index=cl, status=status))

                for si in range(sifat_start, min(sifat_end, len(result.sifat))):
                    sifa = result.sifat[si]
                    for attr in SIFA_ATTRS:
                        val = getattr(sifa, attr, None)
                        conf = getattr(sifa, f"{attr}_conf", 0.0)
                        if val is not None and conf > 0.5:
                            letter_idx = si - sifat_start
                            grade = "GOOD" if conf >= 0.8 else "FAIR"
                            tajweed_updates.append(TajweedUpdate(
                                word_index=wi,
                                letter_index=letter_idx,
                                rule=f"{attr}:{val}",
                                grade=grade,
                            ))

            covered_words = {u.word_index for u in letter_updates}
            mapped_word_indices = {w["word_index"] for w in result.word_phoneme_map}
            min_mapped = min(mapped_word_indices) if mapped_word_indices else 0
            max_mapped = max(mapped_word_indices) if mapped_word_indices else 0
            filled_words = set()
            if ayah.word_to_letters:
                for wi in range(min_mapped, max_mapped + 1):
                    if wi not in covered_words and wi not in mapped_word_indices:
                        filled_words.add(wi)
                        for cw, cl in ayah.word_to_letters.get(wi, []):
                            letter_updates.append(LetterUpdate(word_index=cw, letter_index=cl, status=LetterStatus.NOT_SURE))
            else:
                for cw, cl in ayah.uthmani_char_map:
                    if cw > max_mapped:
                        break
                    if cw >= min_mapped and cw not in covered_words and cw not in mapped_word_indices:
                        filled_words.add(cw)
                        letter_updates.append(LetterUpdate(word_index=cw, letter_index=cl, status=LetterStatus.NOT_SURE))
            if filled_words:
                logger.debug("MUAALEM filled NOT_SURE for missing words: %s", sorted(filled_words))

            if max_confident_word > old_word:
                mapped_between = sum(
                    1 for wi in range(old_word, max_confident_word + 1)
                    if wi in mapped_word_indices
                )
                span = max_confident_word - old_word + 1
                density = mapped_between / span if span > 0 else 0.0

                if density < 0.4:
                    sorted_mapped = sorted(wi for wi in mapped_word_indices if wi > old_word)
                    capped_word = old_word
                    for wi in sorted_mapped:
                        gap = wi - capped_word
                        if gap > 3:
                            break
                        capped_word = wi
                    max_confident_word = capped_word

                if max_confident_word > old_word:
                    self.current_word_index = max_confident_word
                    output.positions.append(PositionEvent(
                        surah_id=ayah.surah_id,
                        ayah_number=ayah.ayah_number,
                        word_index=max_confident_word,
                        confidence=avg_confidence,
                    ))
        else:
            total_words = len(ayah.normalized_words)
            estimated_word = int(coverage_ratio * (total_words - 1))
            estimated_word = min(estimated_word, total_words - 1)

            if estimated_word > self.current_word_index:
                self.current_word_index = estimated_word
                output.positions.append(PositionEvent(
                    surah_id=ayah.surah_id,
                    ayah_number=ayah.ayah_number,
                    word_index=estimated_word,
                    confidence=avg_confidence,
                ))

            if ayah.uthmani_char_map and avg_confidence >= TRACK_THRESHOLD:
                if ayah.word_to_letters:
                    for wi in range(estimated_word + 1):
                        for cw, cl in ayah.word_to_letters.get(wi, []):
                            letter_updates.append(LetterUpdate(
                                word_index=cw, letter_index=cl, status=LetterStatus.NOT_SURE,
                            ))
                else:
                    for cw, cl in ayah.uthmani_char_map:
                        if cw > estimated_word:
                            break
                        letter_updates.append(LetterUpdate(
                            word_index=cw, letter_index=cl, status=LetterStatus.NOT_SURE,
                        ))

            error_event = self._extract_recitation_errors(result, ayah, self.current_word_index)

        if letter_updates:
            output.letter_statuses.append(LetterStatusEvent(
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
                updates=letter_updates,
                confidence=avg_confidence,
            ))

        if tajweed_updates:
            output.tajweed_statuses.append(TajweedStatusEvent(
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
                updates=tajweed_updates,
            ))

        if error_event:
            new_errors = []
            new_keys = set()
            for e in error_event.errors:
                key = (e.error_type, e.uthmani_start, e.uthmani_end, e.expected_phoneme)
                new_keys.add(key)
                if key not in self._last_error_keys:
                    new_errors.append(e)
            self._last_error_keys = new_keys
            if new_errors:
                output.recitation_errors.append(RecitationErrorEvent(
                    surah_id=error_event.surah_id,
                    ayah_number=error_event.ayah_number,
                    errors=new_errors,
                ))

        letter_count = len(letter_updates)
        correct_count = sum(1 for u in letter_updates if u.status == LetterStatus.CORRECT)
        error_count = len(error_event.errors) if error_event else 0
        new_error_count = sum(1 for e in output.recitation_errors for _ in e.errors) if output.recitation_errors else 0
        logger.debug(
            "MUAALEM result: coverage=%.2f conf=%.3f letters=%d correct=%d errors_raw=%d errors_new=%d",
            coverage_ratio, avg_confidence, letter_count, correct_count, error_count, new_error_count,
        )

        total_words = len(ayah.normalized_words)

        if total_words > 0 and self.current_word_index >= total_words - 1 and avg_confidence >= TRACK_THRESHOLD:
            self._muaalem_last_word_count += 1
        else:
            self._muaalem_last_word_count = max(0, self._muaalem_last_word_count - 1)

        logger.debug(
            "MUAALEM completion: word=%d/%d last_word_count=%d complete_count=%d frames=%d coverage=%.2f",
            self.current_word_index, total_words - 1, self._muaalem_last_word_count,
            self._muaalem_complete_count, self._muaalem_frames_tracked, coverage_ratio,
        )

        if self._muaalem_last_word_count >= 2 and self._muaalem_frames_tracked >= 4 and coverage_ratio >= 0.5:
            logger.info("MUAALEM COMPLETED (word-pos): %d:%d", ayah.surah_id, ayah.ayah_number)
            output.ayah_events.append(AyahEvent(
                event_type="ayah.completed",
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
            ))
            self._muaalem_last_word_count = 0
            self._muaalem_complete_count = 0
            self._transition_to_next(output)
            return output

        if coverage_ratio >= AYAH_COMPLETE_RATIO and avg_confidence >= 0.6:
            self._muaalem_complete_count += 1
        else:
            self._muaalem_complete_count = 0

        if total_words > 0 and self._muaalem_complete_count >= 3 and self._muaalem_frames_tracked >= 4:
            logger.info("MUAALEM COMPLETED: %d:%d", ayah.surah_id, ayah.ayah_number)
            output.ayah_events.append(AyahEvent(
                event_type="ayah.completed",
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
            ))
            self._muaalem_complete_count = 0
            self._transition_to_next(output)

        return output

    def process_forced_align_result(self, result: ForcedAlignResult) -> TrackerOutput:
        output = TrackerOutput()
        if self.state != TrackerState.TRACKING:
            return output

        ayah = self.current_ayah
        if not ayah:
            return output

        word_updates = []
        new_confirmed = self._confirmed_word_index

        for wb in result.word_boundaries:
            if wb.word_index <= self._confirmed_word_index:
                continue
            if wb.score >= FORCED_ALIGN_WORD_THRESHOLD:
                word_updates.append(WordStatusUpdate(
                    word_index=wb.word_index,
                    status="ALIGNED",
                    confidence=wb.score,
                ))
                if wb.word_index > new_confirmed:
                    new_confirmed = wb.word_index

        if new_confirmed > self._confirmed_word_index:
            self._confirmed_word_index = new_confirmed
            if new_confirmed > self.current_word_index:
                self.current_word_index = new_confirmed
                output.positions.append(PositionEvent(
                    surah_id=ayah.surah_id,
                    ayah_number=ayah.ayah_number,
                    word_index=new_confirmed,
                    confidence=result.word_boundaries[-1].score if result.word_boundaries else 0.0,
                ))

        if word_updates:
            output.word_statuses.append(WordStatusEvent(
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
                updates=word_updates,
            ))

        total_words = len(ayah.normalized_words)
        if total_words > 0 and new_confirmed >= total_words - 1:
            last_boundary = next(
                (wb for wb in result.word_boundaries if wb.word_index == total_words - 1),
                None,
            )
            if last_boundary and last_boundary.score >= FORCED_ALIGN_WORD_THRESHOLD:
                logger.info(
                    "FORCED_ALIGN COMPLETED: %d:%d", ayah.surah_id, ayah.ayah_number
                )
                output.ayah_events.append(AyahEvent(
                    event_type="ayah.completed",
                    surah_id=ayah.surah_id,
                    ayah_number=ayah.ayah_number,
                ))

        return output

    def process_ayah_muaalem_result(self, result: MuaalemResult, ayah: QuranAyah | None = None) -> TrackerOutput:
        output = TrackerOutput()
        ayah = ayah or self.current_ayah
        if not ayah:
            return output

        avg_confidence = sum(result.confidences) / max(len(result.confidences), 1)
        total_words = len(ayah.normalized_words)

        word_updates = []
        letter_updates = []
        tajweed_updates = []

        error_event = self._extract_recitation_errors(result, ayah, total_words - 1)
        error_affected: set[tuple[int, int]] = set()
        if error_event:
            consonant_errors = [e for e in error_event.errors if e.error_type == "normal"]
            error_affected = self._error_affected_letters(
                result.uthmani_text, consonant_errors, pos_to_wl=ayah.pos_to_wl or None,
            )

        if result.word_phoneme_map and ayah.uthmani_char_map:
            for word_entry in result.word_phoneme_map:
                wi = word_entry["word_index"]
                sifat_start = word_entry["sifat_start"]
                sifat_end = word_entry["sifat_end"]
                word_confs = result.confidences[sifat_start:sifat_end]
                word_avg = sum(word_confs) / max(len(word_confs), 1) if word_confs else 0.0

                has_errors = False
                word_letters = ayah.word_to_letters.get(wi) if ayah.word_to_letters else None
                letter_positions = word_letters or [(cw, cl) for cw, cl in ayah.uthmani_char_map if cw == wi]
                for cw, cl in letter_positions:
                    if (cw, cl) in error_affected:
                        has_errors = True
                        letter_updates.append(LetterUpdate(word_index=cw, letter_index=cl, status=LetterStatus.INCORRECT))
                    else:
                        status = LetterStatus.CORRECT if word_avg >= MUAALEM_CORRECT_THRESHOLD else LetterStatus.NOT_SURE
                        letter_updates.append(LetterUpdate(word_index=cw, letter_index=cl, status=status))

                if has_errors:
                    word_status = "INCORRECT"
                elif word_avg >= MUAALEM_CORRECT_THRESHOLD:
                    word_status = "CORRECT"
                else:
                    word_status = "NOT_SURE"

                word_updates.append(WordStatusUpdate(
                    word_index=wi,
                    status=word_status,
                    confidence=word_avg,
                ))

                for si in range(sifat_start, min(sifat_end, len(result.sifat))):
                    sifa = result.sifat[si]
                    for attr in SIFA_ATTRS:
                        val = getattr(sifa, attr, None)
                        conf = getattr(sifa, f"{attr}_conf", 0.0)
                        if val is not None and conf > 0.5:
                            letter_idx = si - sifat_start
                            grade = "GOOD" if conf >= 0.8 else "FAIR"
                            tajweed_updates.append(TajweedUpdate(
                                word_index=wi,
                                letter_index=letter_idx,
                                rule=f"{attr}:{val}",
                                grade=grade,
                            ))

        if word_updates:
            output.word_statuses.append(WordStatusEvent(
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
                updates=word_updates,
            ))

        if letter_updates:
            output.letter_statuses.append(LetterStatusEvent(
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
                updates=letter_updates,
                confidence=avg_confidence,
            ))

        if tajweed_updates:
            output.tajweed_statuses.append(TajweedStatusEvent(
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
                updates=tajweed_updates,
            ))

        if error_event:
            output.recitation_errors.append(error_event)

        return output

    def process_word_muaalem_result(
        self, result: MuaalemResult, ayah: QuranAyah, target_word: int,
    ) -> TrackerOutput:
        output = TrackerOutput()
        if not result.word_phoneme_map or not ayah.uthmani_char_map:
            return output

        word_entry = None
        for w in result.word_phoneme_map:
            if w["word_index"] == target_word:
                word_entry = w
                break

        if word_entry is None:
            return output

        sifat_start = word_entry["sifat_start"]
        sifat_end = word_entry["sifat_end"]
        word_confs = result.confidences[sifat_start:sifat_end]
        word_avg = sum(word_confs) / max(len(word_confs), 1) if word_confs else 0.0

        error_event = self._extract_recitation_errors(result, ayah, target_word)
        error_affected: set[tuple[int, int]] = set()
        if error_event:
            consonant_errors = [e for e in error_event.errors if e.error_type == "normal"]
            error_affected = self._error_affected_letters(
                result.uthmani_text, consonant_errors, pos_to_wl=ayah.pos_to_wl or None,
            )

        letter_updates = []
        tajweed_updates = []
        has_errors = False

        letter_positions = (
            ayah.word_to_letters.get(target_word)
            if ayah.word_to_letters
            else [(cw, cl) for cw, cl in ayah.uthmani_char_map if cw == target_word]
        )
        if letter_positions:
            for cw, cl in letter_positions:
                if (cw, cl) in error_affected:
                    has_errors = True
                    letter_updates.append(LetterUpdate(
                        word_index=cw, letter_index=cl, status=LetterStatus.INCORRECT,
                    ))
                else:
                    status = LetterStatus.CORRECT if word_avg >= MUAALEM_CORRECT_THRESHOLD else LetterStatus.NOT_SURE
                    letter_updates.append(LetterUpdate(
                        word_index=cw, letter_index=cl, status=status,
                    ))

        for si in range(sifat_start, min(sifat_end, len(result.sifat))):
            sifa = result.sifat[si]
            for attr in SIFA_ATTRS:
                val = getattr(sifa, attr, None)
                conf = getattr(sifa, f"{attr}_conf", 0.0)
                if val is not None and conf > 0.5:
                    letter_idx = si - sifat_start
                    grade = "GOOD" if conf >= 0.8 else "FAIR"
                    tajweed_updates.append(TajweedUpdate(
                        word_index=target_word,
                        letter_index=letter_idx,
                        rule=f"{attr}:{val}",
                        grade=grade,
                    ))

        if has_errors:
            word_status = "INCORRECT"
        elif word_avg >= MUAALEM_CORRECT_THRESHOLD:
            word_status = "CORRECT"
        else:
            word_status = "NOT_SURE"

        output.word_statuses.append(WordStatusEvent(
            surah_id=ayah.surah_id,
            ayah_number=ayah.ayah_number,
            updates=[WordStatusUpdate(
                word_index=target_word,
                status=word_status,
                confidence=word_avg,
            )],
        ))

        if letter_updates:
            output.letter_statuses.append(LetterStatusEvent(
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
                updates=letter_updates,
                confidence=word_avg,
            ))

        if tajweed_updates:
            output.tajweed_statuses.append(TajweedStatusEvent(
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
                updates=tajweed_updates,
            ))

        if error_event:
            output.recitation_errors.append(error_event)

        return output

    @staticmethod
    def _covered_uthmani_range(result: MuaalemResult) -> tuple[int, int]:
        if not result.word_phoneme_map:
            return 0, len(result.uthmani_text)

        covered_words = {w["word_index"] for w in result.word_phoneme_map}
        if not covered_words:
            return 0, len(result.uthmani_text)

        min_word = min(covered_words)
        max_word = max(covered_words)

        words = result.uthmani_text.split()
        pos = 0
        word_ranges: list[tuple[int, int]] = []
        for w in words:
            word_ranges.append((pos, pos + len(w)))
            pos += len(w) + 1

        start = word_ranges[min_word][0] if min_word < len(word_ranges) else 0
        end = word_ranges[max_word][1] if max_word < len(word_ranges) else len(result.uthmani_text)
        return start, end

    @staticmethod
    def _error_affected_letters(
        uthmani_text: str, errors: list[RecitationErrorDetail],
        pos_to_wl: dict[int, tuple[int, int]] | None = None,
    ) -> set[tuple[int, int]]:
        affected: set[tuple[int, int]] = set()
        if pos_to_wl is None:
            words = uthmani_text.split()
            pos_to_wl = {}
            pos = 0
            for word_idx, word in enumerate(words):
                letter_idx = 0
                for ch in word:
                    if not TASHKEEL_PATTERN.match(ch):
                        pos_to_wl[pos] = (word_idx, letter_idx)
                        letter_idx += 1
                    pos += 1
                pos += 1

        for error in errors:
            for p in range(error.uthmani_start, error.uthmani_end):
                if p in pos_to_wl:
                    affected.add(pos_to_wl[p])

        return affected

    @staticmethod
    def _extract_recitation_errors(
        result: MuaalemResult, ayah: QuranAyah, max_word_index: int = -1
    ) -> RecitationErrorEvent | None:
        if not result.phonetizer_mappings or not result.ref_phonemes:
            return None

        if _explain_error is None:
            return None

        try:
            raw_errors = _explain_error(
                result.uthmani_text,
                result.ref_phonemes,
                result.phonemes_text,
                result.phonetizer_mappings,
            )
        except Exception as e:
            logger.warning("Error extraction failed: %s", e)
            return None

        if not raw_errors:
            return None

        _, covered_end = RecitationTracker._covered_uthmani_range(result)

        uthmani_words = result.uthmani_text.split()

        if max_word_index >= 0:
            error_window_start_word = max(0, max_word_index - 2)
            clipped_end_word = min(max_word_index, len(uthmani_words) - 1)
        else:
            error_window_start_word = 0
            clipped_end_word = len(uthmani_words) - 1

        pos = 0
        covered_start = 0
        for i, w in enumerate(uthmani_words):
            if i == error_window_start_word:
                covered_start = pos
            if i >= clipped_end_word:
                covered_end = min(covered_end, pos + len(w))
                break
            pos += len(w) + 1

        logger.debug(
            "MUAALEM errors: max_word=%d window=[%d:%d] (words %d-%d) raw=%d",
            max_word_index, covered_start, covered_end,
            error_window_start_word, clipped_end_word, len(raw_errors),
        )

        filtered_out = 0
        details = []
        for err in raw_errors:
            if err.uthmani_pos[0] < covered_start or err.uthmani_pos[0] >= covered_end:
                filtered_out += 1
                continue

            rule_name = None
            if err.ref_tajweed_rules:
                r = err.ref_tajweed_rules[0]
                rule_name = r.name.en if hasattr(r.name, "en") else str(r.name)

            details.append(RecitationErrorDetail(
                error_type=err.error_type,
                speech_error_type=err.speech_error_type,
                expected_phoneme=err.expected_ph,
                predicted_phoneme=err.preditected_ph,
                uthmani_start=err.uthmani_pos[0],
                uthmani_end=err.uthmani_pos[1],
                tajweed_rule=rule_name,
                expected_len=err.expected_len,
                predicted_len=err.predicted_len,
            ))

        if filtered_out:
            logger.debug("MUAALEM errors: filtered_out=%d kept=%d", filtered_out, len(details))

        if not details:
            return None

        return RecitationErrorEvent(
            surah_id=ayah.surah_id,
            ayah_number=ayah.ayah_number,
            errors=details,
        )

    def _init_phoneme_tracker(self, ayah: QuranAyah):
        self._phoneme_tracker = None
        if self.ipa_database:
            ipa_units = self.ipa_database.get_ipa(ayah.surah_id, ayah.ayah_number)
            if ipa_units:
                self._phoneme_tracker = PhonemeTracker(ipa_units)
                logger.info(
                    "PhonemeTracker initialized for %d:%d (%d IPA units)",
                    ayah.surah_id, ayah.ayah_number, len(ipa_units),
                )

    @property
    def has_phoneme_tracker(self) -> bool:
        return self._phoneme_tracker is not None

    @staticmethod
    def _word_offsets(words: list[str]) -> list[int]:
        offsets = []
        pos = 0
        for w in words:
            offsets.append(pos)
            pos += len(w)
        return offsets

    def reset_locate_votes(self):
        self._locate_votes.clear()
        self._candidates = []
        self._prev_phonetic_query = ""

    def _update_locate_votes(self, candidates: list[MatchCandidate]):
        current_ayahs = {(c.surah_id, c.ayah_number) for c in candidates}
        if len(current_ayahs) > MAX_VOTE_CANDIDATES:
            self._locate_votes.clear()
            return
        for key in list(self._locate_votes):
            if key not in current_ayahs:
                self._locate_votes[key] -= 1
                if self._locate_votes[key] <= 0:
                    del self._locate_votes[key]
        for key in current_ayahs:
            self._locate_votes[key] = self._locate_votes.get(key, 0) + 1

    def _try_vote_locate(
        self, candidates: list[MatchCandidate], confidence: float, output: TrackerOutput,
    ) -> bool:
        if not self._locate_votes:
            return False
        max_votes = max(self._locate_votes.values())
        if max_votes < LOCATE_VOTE_THRESHOLD:
            return False
        top_keys = [k for k, v in self._locate_votes.items() if v == max_votes]
        current_candidates = {
            (c.surah_id, c.ayah_number): c for c in candidates
        }
        if len(top_keys) > 1:
            top_with_candidates = [k for k in top_keys if k in current_candidates]
            if not top_with_candidates:
                return False
            key = max(
                top_with_candidates,
                key=lambda k: (current_candidates[k].match_count, -k[0], -k[1]),
            )
        else:
            key = top_keys[0]
        if key not in current_candidates:
            return False
        best = current_candidates[key]
        if best.match_count < MIN_LOCATE_MATCH_COUNT:
            return False
        logger.info(
            "LOCATING: vote-accepted %d:%d (votes=%d, quality=%d)",
            best.surah_id, best.ayah_number, max_votes, best.match_count,
        )
        self._locate_candidate(best, confidence, output)
        return True

    def _try_strong_match(
        self, candidates: list[MatchCandidate], confidence: float, output: TrackerOutput,
    ) -> bool:
        if len(candidates) < 1 or len(candidates) > MAX_LOCATE_STRONG_CANDIDATES:
            return False
        best = max(candidates, key=lambda c: (c.match_count, -c.start_char))
        if best.match_count < MIN_LOCATE_STRONG_MATCH:
            return False
        strong_ayahs = {
            (c.surah_id, c.ayah_number) for c in candidates
            if c.match_count >= MIN_LOCATE_STRONG_MATCH
        }
        if len(strong_ayahs) > 1:
            return False
        logger.info(
            "LOCATING: strong-match %d:%d (candidates=%d, quality=%d)",
            best.surah_id, best.ayah_number, len(candidates), best.match_count,
        )
        self._locate_candidate(best, confidence, output)
        return True

    def _handle_locating(self, text: str, words: list[str], confidence: float) -> TrackerOutput:
        output = TrackerOutput()

        if len(text) < MIN_LOCATE_CHARS:
            return output

        self._locate_attempts += 1

        phonetic_full = to_phonetic(text)

        if self._prev_phonetic_query and phonetic_full.startswith(self._prev_phonetic_query) and self._candidates:
            candidates = self.prefix_index.narrow(self._candidates, phonetic_full)
            if candidates:
                logger.info("LOCATING: narrowed %d → %d candidates (len=%d)", len(self._candidates), len(candidates), len(phonetic_full))
                self._candidates = candidates
                self._prev_phonetic_query = phonetic_full
                if self._try_strong_match(candidates, confidence, output):
                    return output
                self._update_locate_votes(candidates)
                if self._try_vote_locate(candidates, confidence, output):
                    return output
                if len(candidates) == 1 and len(phonetic_full) >= MIN_LOCATE_UNIQUE_LEN and candidates[0].match_count >= MIN_LOCATE_MATCH_COUNT:
                    self._locate_candidate(candidates[0], confidence, output)
                return output

        offsets = self._word_offsets(words)
        best_candidates: list[MatchCandidate] = []
        best_phonetic: str = ""
        best_match_count = 0
        for offset in offsets:
            suffix = text[offset:]
            if len(suffix) < MIN_LOCATE_CHARS:
                break
            phonetic_suffix = to_phonetic(suffix)
            candidates = self.prefix_index.search(phonetic_suffix)
            if candidates:
                top_count = max(c.match_count for c in candidates)
                if top_count > best_match_count:
                    best_match_count = top_count
                    best_candidates = candidates
                    best_phonetic = phonetic_suffix

        if best_candidates:
            logger.info(
                "LOCATING: search best → %d candidates (len=%d, best_match=%d)",
                len(best_candidates), len(best_phonetic), best_match_count,
            )
            self._candidates = best_candidates
            self._prev_phonetic_query = best_phonetic
            if self._try_strong_match(best_candidates, confidence, output):
                return output
            self._update_locate_votes(best_candidates)
            if self._try_vote_locate(best_candidates, confidence, output):
                return output
            if len(best_candidates) == 1 and len(best_phonetic) >= MIN_LOCATE_UNIQUE_LEN and best_candidates[0].match_count >= MIN_LOCATE_MATCH_COUNT:
                self._locate_candidate(best_candidates[0], confidence, output)
            return output

        logger.info("LOCATING: 0 candidates from all offsets (len=%d)", len(text))
        self._candidates = []
        self._prev_phonetic_query = ""
        if self._locate_attempts >= settings.max_locate_attempts:
            output.locating_timeout = True
            logger.warning("LOCATING: timeout after %d attempts", self._locate_attempts)
        return output

    def _locate_candidate(self, candidate: MatchCandidate, confidence: float, output: TrackerOutput):
        ayah = self.corpus.get_ayah(candidate.surah_id, candidate.ayah_number)
        if not ayah:
            return

        self._locate_attempts = 0
        self.current_ayah = ayah
        self.matched_char_pos = candidate.matched_end
        self.current_word_index = self._char_to_word(ayah, self.matched_char_pos)
        self.state = TrackerState.TRACKING
        self._init_phoneme_tracker(ayah)

        text_len = len(ayah.normalized_text_no_spaces)
        if text_len > 0 and self.matched_char_pos >= text_len * AYAH_COMPLETE_RATIO:
            self._need_advance_to_complete = True

        logger.info(
            "LOCATED: %d:%d word=%d (candidates=1)",
            ayah.surah_id, ayah.ayah_number, self.current_word_index,
        )

        self._auto_complete_muqattaat(ayah, output)

        output.ayah_events.append(AyahEvent(
            event_type="ayah.started",
            surah_id=ayah.surah_id,
            ayah_number=ayah.ayah_number,
            text=ayah.text,
        ))
        output.positions.append(PositionEvent(
            surah_id=ayah.surah_id,
            ayah_number=ayah.ayah_number,
            word_index=self.current_word_index,
            confidence=confidence,
        ))

        matched_indices = set(range(candidate.start_char, self.matched_char_pos))
        letter_event = self._compute_letter_statuses(
            ayah, candidate.start_char, self.matched_char_pos, matched_indices, confidence,
        )
        if letter_event:
            output.letter_statuses.append(letter_event)

    def _auto_complete_muqattaat(self, located_ayah: QuranAyah, output: TrackerOutput):
        if located_ayah.ayah_number <= 1:
            return
        prev = self.corpus.get_ayah(located_ayah.surah_id, located_ayah.ayah_number - 1)
        if not prev or not is_muqattaat(prev.normalized_text_no_spaces):
            return

        logger.info(
            "MUQATTAAT: auto-completing %d:%d before %d:%d",
            prev.surah_id, prev.ayah_number,
            located_ayah.surah_id, located_ayah.ayah_number,
        )
        output.ayah_events.append(AyahEvent(
            event_type="ayah.started",
            surah_id=prev.surah_id,
            ayah_number=prev.ayah_number,
            text=prev.text,
        ))
        if prev.uthmani_char_map:
            all_correct = [
                LetterUpdate(word_index=wi, letter_index=li, status=LetterStatus.CORRECT)
                for wi, li in prev.uthmani_char_map
            ]
            if all_correct:
                output.letter_statuses.append(LetterStatusEvent(
                    surah_id=prev.surah_id,
                    ayah_number=prev.ayah_number,
                    updates=all_correct,
                    confidence=1.0,
                ))
        output.ayah_events.append(AyahEvent(
            event_type="ayah.completed",
            surah_id=prev.surah_id,
            ayah_number=prev.ayah_number,
        ))

    def _handle_tracking(self, transcription: str, confidence: float) -> TrackerOutput:
        output = TrackerOutput()
        ayah = self.current_ayah
        if not ayah:
            return output

        logger.debug(
            "CTC TRACKING %d:%d: '%s' (conf=%.2f, matched=%d/%d)",
            ayah.surah_id, ayah.ayah_number, transcription[:80],
            confidence, self.matched_char_pos, len(ayah.normalized_text_no_spaces),
        )

        text = ayah.normalized_text_no_spaces

        effective_transcription = transcription
        for prev in reversed(self._recent_transcriptions):
            if transcription.startswith(prev) and len(transcription) > len(prev):
                effective_transcription = transcription[len(prev):]
                break

        self._recent_transcriptions.append(transcription)
        if len(self._recent_transcriptions) > 3:
            self._recent_transcriptions.pop(0)

        lookback = min(self.matched_char_pos, len(effective_transcription))
        search_start = self.matched_char_pos - lookback
        search_text = text[search_start:]
        score, start_pos, text_end, matched = self._fuzzy_find(
            effective_transcription, search_text, max_start_range=MAX_SEARCH_RANGE,
        )
        matched = {idx + search_start for idx in matched}
        start_pos += search_start
        text_end += search_start

        if score >= TRACK_THRESHOLD and start_pos <= self.matched_char_pos + MAX_POSITION_JUMP:
            self._consecutive_failures = 0
            old_pos = self.matched_char_pos
            advanced = False
            if text_end > self.matched_char_pos:
                self.matched_char_pos = min(text_end, len(text))
                advanced = True

            if advanced:
                self._need_advance_to_complete = False

            new_word = self._char_to_word(ayah, self.matched_char_pos)
            if new_word > self.current_word_index:
                self.current_word_index = new_word
                output.positions.append(PositionEvent(
                    surah_id=ayah.surah_id,
                    ayah_number=ayah.ayah_number,
                    word_index=self.current_word_index,
                    confidence=score,
                ))

            if self.matched_char_pos > old_pos and score >= settings.letter_confidence_gate:
                letter_event = self._compute_letter_statuses(
                    ayah, old_pos, self.matched_char_pos, matched, score,
                )
                if letter_event:
                    output.letter_statuses.append(letter_event)

            can_complete = self.matched_char_pos >= len(text) * AYAH_COMPLETE_RATIO
            if can_complete and not self._need_advance_to_complete:
                self._ctc_complete_count += 1
                if self._ctc_complete_count >= 2:
                    self._emit_remaining_letters(ayah, output)
                    logger.info("COMPLETED: %d:%d", ayah.surah_id, ayah.ayah_number)
                    output.ayah_events.append(AyahEvent(
                        event_type="ayah.completed",
                        surah_id=ayah.surah_id,
                        ayah_number=ayah.ayah_number,
                    ))
                    self._ctc_complete_count = 0
                    self._transition_to_next(output)
            else:
                self._ctc_complete_count = 0
            return output

        can_check_next = self.matched_char_pos >= len(text) * NEXT_AYAH_CHECK_RATIO
        if can_check_next and self._check_next_ayah(transcription, output):
            return output

        if self._check_ayah_repeat(transcription, output):
            self._consecutive_failures = 0
            return output

        if self._transition_grace > 0:
            self._transition_grace -= 1
            return output

        self._consecutive_failures += 1
        if self._consecutive_failures >= CONSECUTIVE_FAILURES_BEFORE_MISTAKE:
            logger.debug(
                "CTC consecutive failures: %d at word %d for %d:%d",
                self._consecutive_failures, self.current_word_index,
                ayah.surah_id, ayah.ayah_number,
            )
        return output

    def _check_ayah_repeat(self, transcription: str, output: TrackerOutput) -> bool:
        ayah = self.current_ayah
        if not ayah:
            return False

        text = ayah.normalized_text_no_spaces
        if self.matched_char_pos < len(text) * REPEAT_CHECK_RATIO:
            return False

        prefix = text[:NEXT_AYAH_PREFIX_LEN]
        score, _, text_end, _ = self._fuzzy_find(transcription, prefix)
        if score < TRACK_THRESHOLD:
            return False

        logger.info("REPEAT: %d:%d", ayah.surah_id, ayah.ayah_number)
        self.matched_char_pos = text_end
        self.current_word_index = 0
        self._need_advance_to_complete = False
        self._status_votes.clear()
        self._recent_transcriptions.clear()
        self._transition_grace = TRANSITION_GRACE_CYCLES

        output.ayah_events.append(AyahEvent(
            event_type="ayah.started",
            surah_id=ayah.surah_id,
            ayah_number=ayah.ayah_number,
            text=ayah.text,
        ))
        output.positions.append(PositionEvent(
            surah_id=ayah.surah_id,
            ayah_number=ayah.ayah_number,
            word_index=0,
            confidence=score,
        ))
        return True

    def _emit_mistake(self, ayah: QuranAyah, output: TrackerOutput):
        if not ayah.uthmani_char_map:
            return

        word_idx = min(self.current_word_index, len(ayah.normalized_words) - 1)
        updates = []
        for wi, li in ayah.uthmani_char_map:
            if wi != word_idx:
                continue
            key = (wi, li)
            votes = self._status_votes[key]
            votes.append(LetterStatus.INCORRECT)
            if len(votes) > 3:
                votes.pop(0)

            incorrect_count = sum(1 for v in votes if v == LetterStatus.INCORRECT)
            if incorrect_count >= len(votes) / 2:
                status = LetterStatus.INCORRECT
            else:
                status = LetterStatus.NOT_SURE
            updates.append(LetterUpdate(word_index=wi, letter_index=li, status=status))

        if updates:
            output.letter_statuses.append(LetterStatusEvent(
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
                updates=updates,
                confidence=0.0,
            ))

    def _check_next_ayah(self, transcription: str, output: TrackerOutput) -> bool:
        if not self.current_ayah:
            return False

        next_ayah = self.corpus.get_next_ayah(
            self.current_ayah.surah_id, self.current_ayah.ayah_number
        )
        if not next_ayah:
            return False

        score, _, text_end, _ = self._fuzzy_find(
            transcription, next_ayah.normalized_text_no_spaces[:NEXT_AYAH_PREFIX_LEN]
        )
        if score < TRACK_THRESHOLD:
            return False

        current_surah_id = self.current_ayah.surah_id
        self._emit_remaining_letters(self.current_ayah, output)
        logger.info("COMPLETED: %d:%d (transition)", self.current_ayah.surah_id, self.current_ayah.ayah_number)
        output.ayah_events.append(AyahEvent(
            event_type="ayah.completed",
            surah_id=self.current_ayah.surah_id,
            ayah_number=self.current_ayah.ayah_number,
        ))

        if next_ayah.surah_id != current_surah_id:
            output.surah_completed.append(SurahCompletedEvent(
                surah_id=current_surah_id,
                ayah_number=self.current_ayah.ayah_number,
                next_surah_id=next_ayah.surah_id,
            ))

        self.current_ayah = next_ayah
        self.matched_char_pos = text_end
        self.current_word_index = 0
        self._need_advance_to_complete = False
        self._consecutive_failures = 0
        self._status_votes.clear()
        self._recent_transcriptions.clear()
        self._transition_grace = TRANSITION_GRACE_CYCLES
        self._last_error_keys = set()
        self._init_phoneme_tracker(next_ayah)

        logger.info("TRANSITION: %d:%d", next_ayah.surah_id, next_ayah.ayah_number)
        output.ayah_events.append(AyahEvent(
            event_type="ayah.started",
            surah_id=next_ayah.surah_id,
            ayah_number=next_ayah.ayah_number,
            text=next_ayah.text,
        ))
        output.positions.append(PositionEvent(
            surah_id=next_ayah.surah_id,
            ayah_number=next_ayah.ayah_number,
            word_index=0,
            confidence=score,
        ))
        return True

    def _transition_to_next(self, output: TrackerOutput):
        if not self.current_ayah:
            return

        current_surah_id = self.current_ayah.surah_id
        next_ayah = self.corpus.get_next_ayah(
            self.current_ayah.surah_id, self.current_ayah.ayah_number
        )

        if next_ayah and next_ayah.surah_id != current_surah_id:
            output.surah_completed.append(SurahCompletedEvent(
                surah_id=current_surah_id,
                ayah_number=self.current_ayah.ayah_number,
                next_surah_id=next_ayah.surah_id,
            ))
        elif not next_ayah:
            output.surah_completed.append(SurahCompletedEvent(
                surah_id=current_surah_id,
                ayah_number=self.current_ayah.ayah_number,
                next_surah_id=None,
            ))

        if next_ayah:
            self.current_ayah = next_ayah
            self.matched_char_pos = 0
            self.current_word_index = 0
            self._need_advance_to_complete = False
            self._consecutive_failures = 0
            self._status_votes.clear()
            self._recent_transcriptions.clear()
            self._transition_grace = TRANSITION_GRACE_CYCLES
            self._last_error_keys = set()
            self._muaalem_last_word_count = 0
            self._muaalem_frames_tracked = 0
            self._confirmed_word_index = -1
            self._ctc_complete_count = 0
            self._init_phoneme_tracker(next_ayah)

            output.ayah_events.append(AyahEvent(
                event_type="ayah.started",
                surah_id=next_ayah.surah_id,
                ayah_number=next_ayah.ayah_number,
                text=next_ayah.text,
            ))

    def _emit_remaining_letters(self, ayah: QuranAyah, output: TrackerOutput):
        if not ayah.uthmani_char_map:
            return
        end = len(ayah.uthmani_char_map)
        if self.matched_char_pos >= end:
            return
        updates = [
            LetterUpdate(
                word_index=wi,
                letter_index=li,
                status=LetterStatus.NOT_SURE,
            )
            for wi, li in ayah.uthmani_char_map[self.matched_char_pos:]
        ]
        if updates:
            output.letter_statuses.append(LetterStatusEvent(
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
                updates=updates,
                confidence=0.0,
            ))

    @staticmethod
    def _fuzzy_find(query: str, text: str, max_start_range: int = 0) -> tuple[float, int, int, set[int]]:
        if not query or not text:
            return 0.0, 0, 0, set()

        best_score = 0.0
        best_pos = 0
        best_end = 0
        best_matched: set[int] = set()

        search_limit = min(len(text), max_start_range) if max_start_range > 0 else len(text)
        for start in range(search_limit):
            matches = 0
            t_idx = start
            matched_indices: set[int] = set()
            for c_char in query:
                found = False
                for skip in range(MAX_CHAR_SKIP):
                    pos = t_idx + skip
                    if pos < len(text) and phonetic_match(c_char, text[pos]):
                        matches += 1
                        matched_indices.add(pos)
                        t_idx = pos + 1
                        found = True
                        break
                if not found:
                    pass

            text_span = t_idx - start
            denominator = len(query) + max(text_span, 1)
            score = 2 * matches / denominator
            if score > best_score:
                best_score = score
                best_pos = start
                best_end = t_idx
                best_matched = matched_indices

            if best_score >= 0.9:
                break

        return best_score, best_pos, best_end, best_matched

    def _compute_letter_statuses(
        self,
        ayah: QuranAyah,
        old_pos: int,
        new_pos: int,
        matched_text_indices: set[int],
        confidence: float,
    ) -> LetterStatusEvent | None:
        if not ayah.uthmani_char_map or old_pos >= new_pos:
            return None

        updates: list[LetterUpdate] = []
        end = min(new_pos, len(ayah.uthmani_char_map))
        for i in range(old_pos, end):
            word_index, letter_index = ayah.uthmani_char_map[i]
            if i in matched_text_indices:
                status = LetterStatus.CORRECT
            elif confidence < TRACK_THRESHOLD:
                status = LetterStatus.NOT_SURE
            else:
                status = LetterStatus.INCORRECT
            updates.append(LetterUpdate(
                word_index=word_index,
                letter_index=letter_index,
                status=status,
            ))

        if not updates:
            return None

        return LetterStatusEvent(
            surah_id=ayah.surah_id,
            ayah_number=ayah.ayah_number,
            updates=updates,
            confidence=confidence,
        )

    @staticmethod
    def _char_to_word(ayah: QuranAyah, char_pos: int) -> int:
        if ayah.char_to_word_offsets:
            idx = bisect.bisect_right(ayah.char_to_word_offsets, char_pos - 1) if char_pos > 0 else 0
            return min(idx, max(0, len(ayah.normalized_words) - 1))
        count = 0
        for i, word in enumerate(ayah.normalized_words):
            count += len(word)
            if count >= char_pos:
                return i
        return max(0, len(ayah.normalized_words) - 1)

    def reset(self):
        self.state = TrackerState.LOCATING
        self.current_ayah = None
        self.current_word_index = 0
        self.matched_char_pos = 0
        self._candidates = []
        self._prev_phonetic_query = ""
        self._need_advance_to_complete = False
        self._consecutive_failures = 0
        self._status_votes.clear()
        self._recent_transcriptions.clear()
        self._transition_grace = 0
        self._phoneme_tracker = None
        self._muaalem_complete_count = 0
        self._muaalem_last_word_count = 0
        self._muaalem_frames_tracked = 0
        self._last_error_keys = set()
        self._locate_votes = {}
        self._locate_attempts = 0
        self._phoneme_complete_count = 0
        self._confirmed_word_index = -1
