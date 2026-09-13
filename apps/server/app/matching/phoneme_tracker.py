import logging
from dataclasses import dataclass
from enum import Enum

from app.config import settings
from app.quran.ipa_converter import IPAUnit
from app.matching.events import LetterStatus, LetterUpdate, LetterStatusEvent, TajweedStatusEvent

logger = logging.getLogger(__name__)

CORRECT_THRESHOLD = settings.matching_phoneme_correct_threshold
NOT_SURE_THRESHOLD = settings.matching_phoneme_not_sure_threshold
HAMZA_DEFAULT_DISTANCE = 0.5

MIN_ACTUAL_PHONEMES = 3
MATCH_THRESHOLD = settings.matching_phoneme_match_threshold
PER_PHONEME_CEILING = settings.matching_phoneme_per_phoneme_ceiling
MAX_CONSECUTIVE_GAPS = 3
MAX_LOOKAHEAD = 2
GEMINATION_PENALTY = 0.15

IPA_MODIFIERS = frozenset({"ː", "ˤ"})


class Place(Enum):
    BILABIAL = 0
    LABIODENTAL = 1
    DENTAL = 2
    ALVEOLAR = 3
    POSTALVEOLAR = 4
    PALATAL = 5
    VELAR = 6
    UVULAR = 7
    PHARYNGEAL = 8
    GLOTTAL = 9


class Manner(Enum):
    STOP = 0
    FRICATIVE = 1
    AFFRICATE = 2
    NASAL = 3
    TRILL = 4
    LATERAL = 5
    APPROXIMANT = 6
    VOWEL = 7


@dataclass(frozen=True)
class PhonemeFeatures:
    place: Place
    manner: Manner
    voiced: bool
    emphatic: bool = False


FEATURE_DB: dict[str, PhonemeFeatures] = {
    "b": PhonemeFeatures(Place.BILABIAL, Manner.STOP, True),
    "p": PhonemeFeatures(Place.BILABIAL, Manner.STOP, False),
    "t": PhonemeFeatures(Place.ALVEOLAR, Manner.STOP, False),
    "d": PhonemeFeatures(Place.ALVEOLAR, Manner.STOP, True),
    "k": PhonemeFeatures(Place.VELAR, Manner.STOP, False),
    "g": PhonemeFeatures(Place.VELAR, Manner.STOP, True),
    "q": PhonemeFeatures(Place.UVULAR, Manner.STOP, False),
    "ʔ": PhonemeFeatures(Place.GLOTTAL, Manner.STOP, False),

    "f": PhonemeFeatures(Place.LABIODENTAL, Manner.FRICATIVE, False),
    "v": PhonemeFeatures(Place.LABIODENTAL, Manner.FRICATIVE, True),
    "θ": PhonemeFeatures(Place.DENTAL, Manner.FRICATIVE, False),
    "ð": PhonemeFeatures(Place.DENTAL, Manner.FRICATIVE, True),
    "s": PhonemeFeatures(Place.ALVEOLAR, Manner.FRICATIVE, False),
    "z": PhonemeFeatures(Place.ALVEOLAR, Manner.FRICATIVE, True),
    "ʃ": PhonemeFeatures(Place.POSTALVEOLAR, Manner.FRICATIVE, False),
    "ʒ": PhonemeFeatures(Place.POSTALVEOLAR, Manner.FRICATIVE, True),
    "x": PhonemeFeatures(Place.VELAR, Manner.FRICATIVE, False),
    "ɣ": PhonemeFeatures(Place.VELAR, Manner.FRICATIVE, True),
    "ħ": PhonemeFeatures(Place.PHARYNGEAL, Manner.FRICATIVE, False),
    "ʕ": PhonemeFeatures(Place.PHARYNGEAL, Manner.FRICATIVE, True),
    "h": PhonemeFeatures(Place.GLOTTAL, Manner.FRICATIVE, False),

    "sˤ": PhonemeFeatures(Place.ALVEOLAR, Manner.FRICATIVE, False, emphatic=True),
    "dˤ": PhonemeFeatures(Place.ALVEOLAR, Manner.STOP, True, emphatic=True),
    "tˤ": PhonemeFeatures(Place.ALVEOLAR, Manner.STOP, False, emphatic=True),
    "ðˤ": PhonemeFeatures(Place.DENTAL, Manner.FRICATIVE, True, emphatic=True),

    "dʒ": PhonemeFeatures(Place.POSTALVEOLAR, Manner.AFFRICATE, True),

    "m": PhonemeFeatures(Place.BILABIAL, Manner.NASAL, True),
    "n": PhonemeFeatures(Place.ALVEOLAR, Manner.NASAL, True),

    "r": PhonemeFeatures(Place.ALVEOLAR, Manner.TRILL, True),
    "l": PhonemeFeatures(Place.ALVEOLAR, Manner.LATERAL, True),

    "w": PhonemeFeatures(Place.BILABIAL, Manner.APPROXIMANT, True),
    "j": PhonemeFeatures(Place.PALATAL, Manner.APPROXIMANT, True),

    "a": PhonemeFeatures(Place.PHARYNGEAL, Manner.VOWEL, True),
    "aː": PhonemeFeatures(Place.PHARYNGEAL, Manner.VOWEL, True),
    "i": PhonemeFeatures(Place.PALATAL, Manner.VOWEL, True),
    "iː": PhonemeFeatures(Place.PALATAL, Manner.VOWEL, True),
    "u": PhonemeFeatures(Place.VELAR, Manner.VOWEL, True),
    "uː": PhonemeFeatures(Place.VELAR, Manner.VOWEL, True),
    "e": PhonemeFeatures(Place.PALATAL, Manner.VOWEL, True),
    "o": PhonemeFeatures(Place.VELAR, Manner.VOWEL, True),
    "ə": PhonemeFeatures(Place.PHARYNGEAL, Manner.VOWEL, True),
    "ɛ": PhonemeFeatures(Place.PALATAL, Manner.VOWEL, True),
    "ɔ": PhonemeFeatures(Place.VELAR, Manner.VOWEL, True),
    "ɪ": PhonemeFeatures(Place.PALATAL, Manner.VOWEL, True),
    "ʊ": PhonemeFeatures(Place.VELAR, Manner.VOWEL, True),
    "ɑ": PhonemeFeatures(Place.PHARYNGEAL, Manner.VOWEL, True),
    "ŋ": PhonemeFeatures(Place.VELAR, Manner.NASAL, True),
    "ɲ": PhonemeFeatures(Place.PALATAL, Manner.NASAL, True),
    "ɾ": PhonemeFeatures(Place.ALVEOLAR, Manner.TRILL, True),
}


def split_ipa(ipa: str) -> list[str]:
    phonemes: list[str] = []
    i = 0
    while i < len(ipa):
        if i + 1 < len(ipa) and ipa[i:i + 2] in FEATURE_DB:
            token = ipa[i:i + 2]
            i += 2
        else:
            token = ipa[i]
            i += 1
        while i < len(ipa) and ipa[i] in IPA_MODIFIERS:
            token += ipa[i]
            i += 1
        phonemes.append(token)
    return phonemes


def _deduplicate(chars: list[str]) -> list[str]:
    result: list[str] = []
    for c in chars:
        if not result or c != result[-1]:
            result.append(c)
    return result


def ipa_distance(a: str, b: str) -> float:
    if a == b:
        return 0.0

    a_base = a.rstrip("ː")
    b_base = b.rstrip("ː")
    if a_base == b_base:
        return 0.1

    feat_a = FEATURE_DB.get(a) or FEATURE_DB.get(a_base)
    feat_b = FEATURE_DB.get(b) or FEATURE_DB.get(b_base)

    if feat_a is None or feat_b is None:
        return 0.8

    dist = 0.0
    if feat_a.place != feat_b.place:
        place_diff = abs(feat_a.place.value - feat_b.place.value)
        dist += min(place_diff * 0.1, 0.4)
    if feat_a.manner != feat_b.manner:
        dist += 0.3
    if feat_a.voiced != feat_b.voiced:
        dist += 0.15
    if feat_a.emphatic != feat_b.emphatic:
        dist += 0.15

    return min(dist, 1.0)


@dataclass
class AlignmentPair:
    expected_idx: int | None
    actual_idx: int | None
    distance: float


def compute_letter_statuses_from_alignment(
    alignment: list[AlignmentPair],
    expected_units: list[IPAUnit],
    surah_id: int,
    ayah_number: int,
    start_unit: int,
    confidence: float,
) -> LetterStatusEvent | None:
    updates: list[LetterUpdate] = []
    seen: set[tuple[int, int]] = set()

    for pair in alignment:
        if pair.expected_idx is None:
            continue

        unit_idx = start_unit + pair.expected_idx
        if unit_idx >= len(expected_units):
            continue

        unit = expected_units[unit_idx]
        key = (unit.arabic_word_index, unit.arabic_letter_index)
        if key in seen:
            continue
        seen.add(key)

        if pair.distance < CORRECT_THRESHOLD:
            status = LetterStatus.CORRECT
        elif pair.distance < NOT_SURE_THRESHOLD:
            status = LetterStatus.NOT_SURE
        else:
            status = LetterStatus.INCORRECT

        updates.append(LetterUpdate(
            word_index=unit.arabic_word_index,
            letter_index=unit.arabic_letter_index,
            status=status,
        ))

    if not updates:
        return None

    return LetterStatusEvent(
        surah_id=surah_id,
        ayah_number=ayah_number,
        updates=updates,
        confidence=confidence,
    )


@dataclass
class PhonemeTrackResult:
    letter_event: LetterStatusEvent | None = None
    tajweed_event: TajweedStatusEvent | None = None


class PhonemeTracker:
    def __init__(self, expected_units: list[IPAUnit]):
        self.expected_units = expected_units
        self.expected_phonemes = [u.ipa for u in expected_units]
        self.matched_unit_pos: int = 0
        self._consecutive_failures: int = 0

    def process(
        self,
        actual_phonemes: list[str],
        surah_id: int,
        ayah_number: int,
        confidence: float,
    ) -> PhonemeTrackResult:
        result = PhonemeTrackResult()

        if len(actual_phonemes) < MIN_ACTUAL_PHONEMES:
            return result

        if not self.expected_units:
            return result

        actual_pos = 0
        consecutive_gaps = 0
        matches: list[tuple[int, int | None, float]] = []

        for unit_idx, unit in enumerate(self.expected_units):
            chars = split_ipa(unit.ipa)

            if not chars:
                safe_idx = min(actual_pos, len(actual_phonemes) - 1)
                matches.append((unit_idx, safe_idx, 0.0))
                consecutive_gaps = 0
                continue

            if chars == ["ʔ"]:
                safe_idx = min(actual_pos, len(actual_phonemes) - 1)
                matches.append((unit_idx, safe_idx, HAMZA_DEFAULT_DISTANCE))
                consecutive_gaps = 0
                continue

            matched, match_start, match_len, distance = self._match_unit(
                chars, actual_phonemes, actual_pos,
            )

            if matched:
                matches.append((unit_idx, match_start, distance))
                actual_pos = match_start + match_len
                consecutive_gaps = 0
            else:
                matches.append((unit_idx, None, 1.0))
                consecutive_gaps += 1
                if consecutive_gaps >= MAX_CONSECUTIVE_GAPS:
                    break

        matched_pairs = [
            (idx, aidx, dist)
            for idx, aidx, dist in matches
            if aidx is not None
        ]
        if not matched_pairs:
            self._consecutive_failures += 1
            return result

        furthest_unit = max(idx for idx, _, _ in matched_pairs)
        new_pos = furthest_unit + 1

        if new_pos <= self.matched_unit_pos:
            self._consecutive_failures += 1
            return result

        self._consecutive_failures = 0
        old_pos = self.matched_unit_pos

        alignment: list[AlignmentPair] = []
        for unit_idx, actual_idx, distance in matches:
            if unit_idx < old_pos:
                continue
            if unit_idx > furthest_unit:
                break
            alignment.append(AlignmentPair(
                expected_idx=unit_idx - old_pos,
                actual_idx=actual_idx,
                distance=distance,
            ))

        result.letter_event = compute_letter_statuses_from_alignment(
            alignment,
            self.expected_units,
            surah_id,
            ayah_number,
            old_pos,
            confidence,
        )

        from app.matching.tajweed_grader import grade_tajweed
        result.tajweed_event = grade_tajweed(
            alignment,
            self.expected_units,
            old_pos,
            surah_id,
            ayah_number,
        )

        self.matched_unit_pos = new_pos
        return result

    def _match_unit(
        self,
        expected_chars: list[str],
        actual_phonemes: list[str],
        start_pos: int,
    ) -> tuple[bool, int | None, int, float]:
        for offset in range(MAX_LOOKAHEAD + 1):
            pos = start_pos + offset
            if pos + len(expected_chars) > len(actual_phonemes):
                break
            matched, distance = self._try_match_at(
                expected_chars, actual_phonemes, pos,
            )
            if matched:
                return True, pos, len(expected_chars), distance

        deduped = _deduplicate(expected_chars)
        if len(deduped) < len(expected_chars):
            for offset in range(MAX_LOOKAHEAD + 1):
                pos = start_pos + offset
                if pos + len(deduped) > len(actual_phonemes):
                    break
                matched, distance = self._try_match_at(
                    deduped, actual_phonemes, pos,
                )
                if matched:
                    return True, pos, len(deduped), distance + GEMINATION_PENALTY

        return False, None, 0, 1.0

    def _try_match_at(
        self,
        expected_chars: list[str],
        actual_phonemes: list[str],
        pos: int,
    ) -> tuple[bool, float]:
        total_distance = 0.0
        for i, exp in enumerate(expected_chars):
            dist = ipa_distance(exp, actual_phonemes[pos + i])
            if dist > PER_PHONEME_CEILING:
                return False, 1.0
            total_distance += dist
        avg = total_distance / len(expected_chars)
        if avg >= MATCH_THRESHOLD:
            return False, 1.0
        return True, avg

    @property
    def progress(self) -> float:
        if not self.expected_phonemes:
            return 1.0
        return self.matched_unit_pos / len(self.expected_phonemes)

    @property
    def is_complete(self) -> bool:
        return self.progress >= settings.matching_ayah_complete_ratio

    def word_index_at_position(self) -> int:
        if self.matched_unit_pos >= len(self.expected_units):
            if self.expected_units:
                return self.expected_units[-1].arabic_word_index
            return 0
        return self.expected_units[self.matched_unit_pos].arabic_word_index
