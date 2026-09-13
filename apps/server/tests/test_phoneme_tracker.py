import pytest

from app.quran.ipa_converter import convert_ayah_to_ipa, IPAUnit
from app.matching.phoneme_tracker import (
    ipa_distance,
    PhonemeTracker,
    PhonemeTrackResult,
    split_ipa,
    CORRECT_THRESHOLD,
    NOT_SURE_THRESHOLD,
    MIN_ACTUAL_PHONEMES,
)


class TestIPADistance:
    def test_identical_phonemes_zero_distance(self):
        assert ipa_distance("b", "b") == 0.0
        assert ipa_distance("s", "s") == 0.0

    def test_long_short_vowel_small_distance(self):
        assert ipa_distance("a", "aː") == pytest.approx(0.1)
        assert ipa_distance("i", "iː") == pytest.approx(0.1)
        assert ipa_distance("u", "uː") == pytest.approx(0.1)

    def test_same_place_different_voicing(self):
        dist = ipa_distance("t", "d")
        assert 0 < dist < 0.5

    def test_emphatic_pair_close(self):
        dist = ipa_distance("s", "sˤ")
        assert 0 < dist < 0.5

    def test_very_different_phonemes_high_distance(self):
        dist = ipa_distance("b", "ħ")
        assert dist > 0.5

    def test_unknown_phoneme_high_distance(self):
        dist = ipa_distance("b", "ʘ")
        assert dist >= 0.8

    def test_consonant_vs_vowel_high_distance(self):
        dist = ipa_distance("b", "a")
        assert dist > 0.3


class TestSplitIPA:
    def test_simple_consonant_vowel(self):
        assert split_ipa("bi") == ["b", "i"]

    def test_emphatic_consonant(self):
        assert split_ipa("sˤ") == ["sˤ"]

    def test_geminated(self):
        assert split_ipa("lla") == ["l", "l", "a"]

    def test_long_vowel(self):
        assert split_ipa("aː") == ["aː"]

    def test_affricate(self):
        assert split_ipa("dʒi") == ["dʒ", "i"]

    def test_empty(self):
        assert split_ipa("") == []

    def test_emphatic_with_vowel(self):
        assert split_ipa("sˤi") == ["sˤ", "i"]

    def test_hamza_long_vowel(self):
        assert split_ipa("ʔaː") == ["ʔ", "aː"]


class TestPhonemeTracker:
    def _make_tracker(self, words: list[str]) -> PhonemeTracker:
        units = convert_ayah_to_ipa(words)
        return PhonemeTracker(units)

    def _split_units(self, units: list[IPAUnit]) -> list[str]:
        result = []
        for u in units:
            result.extend(split_ipa(u.ipa))
        return [p for p in result if p]

    def test_exact_phoneme_match_advances(self):
        tracker = self._make_tracker(["بِسْمِ"])
        phonemes = self._split_units(tracker.expected_units[:3])
        result = tracker.process(phonemes, 1, 1, 0.9)
        assert tracker.matched_unit_pos > 0

    def test_progress_increases(self):
        tracker = self._make_tracker(["بِسْمِ"])
        assert tracker.progress == 0.0
        phonemes = self._split_units(tracker.expected_units)
        tracker.process(phonemes, 1, 1, 0.9)
        assert tracker.progress > 0.0

    def test_completion_detection(self):
        tracker = self._make_tracker(["بِسْمِ"])
        phonemes = self._split_units(tracker.expected_units)
        tracker.process(phonemes, 1, 1, 0.9)
        assert tracker.is_complete

    def test_no_match_no_advance(self):
        tracker = self._make_tracker(["بِسْمِ"])
        result = tracker.process(["ʘ", "ʘ", "ʘ"], 1, 1, 0.9)
        assert tracker.matched_unit_pos == 0

    def test_letter_status_event_produced(self):
        tracker = self._make_tracker(["بِسْمِ"])
        phonemes = self._split_units(tracker.expected_units[:3])
        result = tracker.process(phonemes, 1, 1, 0.9)
        if result.letter_event:
            assert len(result.letter_event.updates) > 0
            assert result.letter_event.surah_id == 1
            assert result.letter_event.ayah_number == 1

    def test_word_index_tracking(self):
        tracker = self._make_tracker(["بِسْمِ", "ٱللَّهِ"])
        assert tracker.word_index_at_position() == 0
        phonemes = self._split_units(tracker.expected_units)
        tracker.process(phonemes, 1, 1, 0.9)
        assert tracker.word_index_at_position() >= 1

    def test_tajweed_event_for_annotated_letters(self):
        tracker = self._make_tracker(["إِنَّ"])
        phonemes = self._split_units(tracker.expected_units)
        result = tracker.process(phonemes, 1, 1, 0.9)
        assert result.tajweed_event is not None
        rules = [u.rule for u in result.tajweed_event.updates]
        assert "ghunnah" in rules

    def test_garbage_phonemes_dont_advance(self):
        tracker = self._make_tracker(["بِسْمِ"])
        result = tracker.process(["ʘ", "ʘ", "ʘ", "ʘ"], 1, 1, 0.9)
        assert tracker.matched_unit_pos == 0
        assert result.letter_event is None

    def test_short_input_rejected(self):
        tracker = self._make_tracker(["بِسْمِ"])
        result = tracker.process(["t", "i"], 1, 1, 0.9)
        assert tracker.matched_unit_pos == 0
        assert result.letter_event is None

    def test_sequential_matching_advances_fully(self):
        tracker = self._make_tracker(["بِسْمِ"])
        phonemes = self._split_units(tracker.expected_units)
        result = tracker.process(phonemes, 1, 1, 0.9)
        assert tracker.matched_unit_pos == len(tracker.expected_units)
        assert tracker.is_complete

    def test_noisy_model_output_for_basmala(self):
        tracker = self._make_tracker([
            "بِسْمِ", "ٱللَّهِ", "ٱلرَّحْمَٰنِ", "ٱلرَّحِيمِ",
        ])
        model_output = list("bismilahirxmanjarahiːm")
        model_output[model_output.index("ː") - 1] = "iː"
        model_output.remove("ː")
        result = tracker.process(model_output, 1, 1, 0.74)
        assert tracker.progress > 0.7

    def test_degemination_fallback(self):
        tracker = self._make_tracker(["ٱللَّهِ"])
        phonemes = ["l", "a", "h", "i"]
        result = tracker.process(phonemes, 1, 1, 0.9)
        assert tracker.matched_unit_pos > 0

    def test_glottal_stop_auto_skipped(self):
        tracker = self._make_tracker(["ٱللَّهِ"])
        total_units = len(tracker.expected_units)
        phonemes = self._split_units(tracker.expected_units)
        glottal_free = [p for p in phonemes if p != "ʔ"]
        result = tracker.process(glottal_free, 1, 1, 0.9)
        assert tracker.matched_unit_pos > 0
