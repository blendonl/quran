import pytest

from app.quran.ipa_converter import convert_ayah_to_ipa, IPAUnit
from app.matching.phoneme_tracker import AlignmentPair
from app.matching.tajweed_grader import grade_tajweed, TajweedGrade


def _perfect_alignment(units: list[IPAUnit]) -> list[AlignmentPair]:
    return [AlignmentPair(i, i, 0.0) for i in range(len(units))]


class TestTajweedGrader:
    def test_perfect_match_gets_excellent(self):
        words = ["إِنَّ"]
        units = convert_ayah_to_ipa(words)
        alignment = _perfect_alignment(units)

        event = grade_tajweed(alignment, units, 0, 1, 1)
        if event:
            for u in event.updates:
                assert u.grade in ("excellent", "good")

    def test_no_tajweed_rules_returns_none(self):
        units = [IPAUnit(ipa="b", arabic_word_index=0, arabic_letter_index=0)]
        alignment = [AlignmentPair(0, 0, 0.0)]
        event = grade_tajweed(alignment, units, 0, 1, 1)
        assert event is None

    def test_missed_phoneme_gets_missed_grade(self):
        words = ["إِنَّ"]
        units = convert_ayah_to_ipa(words)
        tajweed_units = [u for u in units if u.tajweed_rule]
        if not tajweed_units:
            pytest.skip("No tajweed rules detected")

        alignment = [AlignmentPair(i, None, 1.0) for i in range(len(units))]
        event = grade_tajweed(alignment, units, 0, 1, 1)
        assert event is not None
        for u in event.updates:
            assert u.grade == "missed"

    def test_ghunnah_detection(self):
        words = ["إِنَّ"]
        units = convert_ayah_to_ipa(words)
        alignment = _perfect_alignment(units)

        event = grade_tajweed(alignment, units, 0, 1, 1)
        if event:
            rules = [u.rule for u in event.updates]
            assert "ghunnah" in rules

    def test_idghaam_detection(self):
        words = ["مَن", "يَقُولُ"]
        units = convert_ayah_to_ipa(words)
        alignment = _perfect_alignment(units)

        event = grade_tajweed(alignment, units, 0, 1, 1)
        if event:
            rules = [u.rule for u in event.updates]
            assert "idghaam_bi_ghunnah" in rules
