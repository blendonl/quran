import logging
from enum import Enum

from app.config import settings
from app.quran.ipa_converter import IPAUnit
from app.matching.phoneme_tracker import AlignmentPair, ipa_distance
from app.matching.events import TajweedUpdate, TajweedStatusEvent

logger = logging.getLogger(__name__)


class TajweedGrade(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    NEEDS_WORK = "needs_work"
    MISSED = "missed"



def grade_tajweed(
    alignment: list[AlignmentPair],
    expected_units: list[IPAUnit],
    start_unit: int,
    surah_id: int,
    ayah_number: int,
) -> TajweedStatusEvent | None:
    updates: list[TajweedUpdate] = []
    seen: set[tuple[int, int]] = set()

    for pair in alignment:
        if pair.expected_idx is None:
            continue

        unit_idx = start_unit + pair.expected_idx
        if unit_idx >= len(expected_units):
            continue

        unit = expected_units[unit_idx]
        if not unit.tajweed_rule:
            continue

        key = (unit.arabic_word_index, unit.arabic_letter_index)
        if key in seen:
            continue
        seen.add(key)

        grade = _grade_rule(unit, pair)
        updates.append(TajweedUpdate(
            word_index=unit.arabic_word_index,
            letter_index=unit.arabic_letter_index,
            rule=unit.tajweed_rule,
            grade=grade.value,
        ))

    if not updates:
        return None

    return TajweedStatusEvent(
        surah_id=surah_id,
        ayah_number=ayah_number,
        updates=updates,
    )


def _grade_rule(unit: IPAUnit, pair: AlignmentPair) -> TajweedGrade:
    if pair.actual_idx is None:
        return TajweedGrade.MISSED

    if pair.distance < settings.matching_tajweed_excellent:
        return TajweedGrade.EXCELLENT
    if pair.distance < settings.matching_tajweed_good:
        return TajweedGrade.GOOD
    if pair.distance < settings.matching_tajweed_needs_work:
        return TajweedGrade.NEEDS_WORK
    return TajweedGrade.MISSED
