import pytest

from app.quran.ipa_converter import convert_ayah_to_ipa, ayah_ipa_to_string, IPAUnit
from app.quran.qiraat import HAFS_CONFIG


AL_FATIHAH_1 = ["بِسْمِ", "ٱللَّهِ", "ٱلرَّحْمَـٰنِ", "ٱلرَّحِيمِ"]
AL_FATIHAH_2 = ["ٱلْحَمْدُ", "لِلَّهِ", "رَبِّ", "ٱلْعَـٰلَمِينَ"]


class TestIPAConverter:
    def test_converts_bismillah_to_ipa_units(self):
        units = convert_ayah_to_ipa(AL_FATIHAH_1)
        assert len(units) > 0
        assert all(isinstance(u, IPAUnit) for u in units)

    def test_ipa_string_contains_expected_phonemes(self):
        units = convert_ayah_to_ipa(AL_FATIHAH_1)
        ipa = ayah_ipa_to_string(units)
        assert "b" in ipa
        assert "s" in ipa
        assert "m" in ipa
        assert "r" in ipa
        assert "ħ" in ipa

    def test_word_indices_are_valid(self):
        units = convert_ayah_to_ipa(AL_FATIHAH_1)
        for u in units:
            assert 0 <= u.arabic_word_index < len(AL_FATIHAH_1)

    def test_shadda_produces_gemination(self):
        units = convert_ayah_to_ipa(AL_FATIHAH_1)
        geminated = [u for u in units if u.is_geminated]
        assert len(geminated) > 0
        for u in geminated:
            base_ipa = u.ipa.replace("a", "").replace("i", "").replace("u", "")
            assert len(base_ipa) >= 2

    def test_madd_detected_in_raheem(self):
        units = convert_ayah_to_ipa(AL_FATIHAH_1)
        madd_units = [u for u in units if u.madd_type is not None]
        assert len(madd_units) > 0

    def test_alhamdu_lillah(self):
        units = convert_ayah_to_ipa(AL_FATIHAH_2)
        ipa = ayah_ipa_to_string(units)
        assert "ħ" in ipa
        assert "l" in ipa

    def test_empty_words_returns_empty(self):
        units = convert_ayah_to_ipa([])
        assert units == []

    def test_all_units_have_ipa(self):
        units = convert_ayah_to_ipa(AL_FATIHAH_1)
        for u in units:
            assert isinstance(u.ipa, str)


class TestTajweedDetection:
    def test_detects_idghaam_in_man_yaqul(self):
        words = ["مَن", "يَقُولُ"]
        units = convert_ayah_to_ipa(words)
        rules = [u.tajweed_rule for u in units if u.tajweed_rule]
        assert "idghaam_bi_ghunnah" in rules

    def test_detects_ikhfaa(self):
        words = ["مِن", "قَبْلِ"]
        units = convert_ayah_to_ipa(words)
        rules = [u.tajweed_rule for u in units if u.tajweed_rule]
        assert "ikhfaa" in rules

    def test_detects_iqlab(self):
        words = ["مِنْ", "بَعْدِ"]
        units = convert_ayah_to_ipa(words)
        rules = [u.tajweed_rule for u in units if u.tajweed_rule]
        assert "iqlab" in rules

    def test_detects_izhar(self):
        words = ["مِنْ", "عِلْمٍ"]
        units = convert_ayah_to_ipa(words)
        rules = [u.tajweed_rule for u in units if u.tajweed_rule]
        assert "izhar" in rules

    def test_detects_qalqalah(self):
        words = ["يَخْلُقْ"]
        units = convert_ayah_to_ipa(words)
        rules = [u.tajweed_rule for u in units if u.tajweed_rule]
        assert "qalqalah" in rules

    def test_detects_ghunnah_shadda_noon(self):
        words = ["إِنَّ"]
        units = convert_ayah_to_ipa(words)
        rules = [u.tajweed_rule for u in units if u.tajweed_rule]
        assert "ghunnah" in rules
