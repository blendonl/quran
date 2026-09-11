from app.matching.phonetic import (
    ipa_distance,
    phonetic_match,
    phonetic_similar,
    to_phonetic,
)


class TestIpaDistance:
    def test_identical_chars_zero(self):
        assert ipa_distance("س", "س") == 0.0

    def test_sad_sin_close(self):
        d = ipa_distance("ص", "س")
        assert d < 0.1

    def test_sad_lam_far(self):
        d = ipa_distance("ص", "ل")
        assert d > 0.1

    def test_ta_tta_close(self):
        d = ipa_distance("ت", "ط")
        assert d < 0.1

    def test_dal_dad_close(self):
        d = ipa_distance("د", "ض")
        assert d < 0.1

    def test_ba_mim_moderate(self):
        d = ipa_distance("ب", "م")
        assert 0.0 < d < 0.3

    def test_symmetric(self):
        d1 = ipa_distance("ص", "س")
        d2 = ipa_distance("س", "ص")
        assert d1 == d2

    def test_cache_consistency(self):
        d1 = ipa_distance("ق", "ك")
        d2 = ipa_distance("ق", "ك")
        assert d1 == d2

    def test_unknown_char_high_distance(self):
        d = ipa_distance("ب", "X")
        assert d > 0.3

    def test_emphatic_pairs_close(self):
        for plain, emphatic in [("ت", "ط"), ("د", "ض"), ("س", "ص")]:
            d = ipa_distance(plain, emphatic)
            assert d < 0.1, f"{plain} vs {emphatic}: {d}"

    def test_distant_pair(self):
        d = ipa_distance("ج", "ا")
        assert d > 0.5


class TestPhoneticSimilar:
    def test_similar_pair(self):
        assert phonetic_similar("ص", "س")

    def test_dissimilar_pair(self):
        assert not phonetic_similar("ج", "ا", threshold=0.3)


class TestPhoneticMatch:
    def test_same_group(self):
        assert phonetic_match("س", "ص")

    def test_different_groups(self):
        assert not phonetic_match("ب", "ل")

    def test_identical(self):
        assert phonetic_match("ب", "ب")


class TestToPhonetic:
    def test_canonicalizes_group_members(self):
        assert to_phonetic("ص") == to_phonetic("س")

    def test_preserves_non_group_chars(self):
        assert to_phonetic("ع") == "ع"
