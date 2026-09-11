import json
import tempfile
from pathlib import Path

import pytest

from app.quran.corpus import QuranCorpus, _build_uthmani_char_map
from app.matching.prefix_index import PrefixIndex
from app.matching.tracker import (
    RecitationTracker,
    TrackerState,
    LetterStatus,
    CONSECUTIVE_FAILURES_BEFORE_MISTAKE,
)
from app.matching.phonetic import phonetic_match, phonetic_key, to_phonetic
from app.transcription.ctc_result import CTCResult


@pytest.fixture
def corpus():
    data = {
        "surahs": [
            {
                "id": 1,
                "name_simple": "Al-Fatihah",
                "name_arabic": "الفاتحة",
                "verses_count": 3,
                "ayahs": [
                    {
                        "ayah_number": 1,
                        "verse_key": "1:1",
                        "text_uthmani": "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
                    },
                    {
                        "ayah_number": 2,
                        "verse_key": "1:2",
                        "text_uthmani": "ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ",
                    },
                    {
                        "ayah_number": 3,
                        "verse_key": "1:3",
                        "text_uthmani": "ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
                    },
                ],
            }
        ]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f, ensure_ascii=False)
        f.flush()
        return QuranCorpus(Path(f.name))


@pytest.fixture
def tracker(corpus):
    prefix_index = PrefixIndex(corpus)
    return RecitationTracker(corpus, prefix_index)


def _locate(tracker):
    tracker.process_ctc_result(CTCResult(characters="الحمد لله رب العالمين", confidence=0.9))
    assert tracker.state == TrackerState.TRACKING


class TestPhoneticGroups:
    def test_sibilants_match(self):
        assert phonetic_match("س", "ص")
        assert phonetic_match("س", "ث")
        assert phonetic_match("ص", "ث")

    def test_sonorants_no_longer_grouped(self):
        assert not phonetic_match("ل", "ر")
        assert not phonetic_match("ل", "ن")
        assert not phonetic_match("ر", "ن")

    def test_bilabials_match(self):
        assert phonetic_match("ب", "م")

    def test_semivowels_match(self):
        assert phonetic_match("و", "ا")
        assert phonetic_match("و", "ي")
        assert phonetic_match("ا", "ي")

    def test_hamza_ain_no_longer_grouped(self):
        assert not phonetic_match("ء", "ع")

    def test_unrelated_dont_match(self):
        assert not phonetic_match("ب", "ق")
        assert not phonetic_match("س", "ل")

    def test_identical_always_match(self):
        assert phonetic_match("ب", "ب")
        assert phonetic_match("ك", "ك")

    def test_multi_group_membership(self):
        key = phonetic_key("ذ")
        assert isinstance(key, frozenset)
        assert len(key) > 1

    def test_to_phonetic_consistent(self):
        text = "بسم"
        result = to_phonetic(text)
        assert len(result) == 3


class TestConsecutiveFailures:
    def test_no_mistake_on_single_failure(self, tracker):
        _locate(tracker)
        result = tracker.process_ctc_result(
            CTCResult(characters="كلمات عشوائية تماما لاعلاقة", confidence=0.9)
        )
        assert len(result.letter_statuses) == 0

    def test_mistake_after_threshold(self, tracker):
        _locate(tracker)
        for _ in range(CONSECUTIVE_FAILURES_BEFORE_MISTAKE - 1):
            result = tracker.process_ctc_result(
                CTCResult(characters="كلمات عشوائية تماما لاعلاقة", confidence=0.9)
            )
            assert len(result.letter_statuses) == 0

        result = tracker.process_ctc_result(
            CTCResult(characters="كلمات عشوائية تماما لاعلاقة", confidence=0.9)
        )
        assert len(result.letter_statuses) > 0

    def test_counter_resets_on_success(self, tracker):
        tracker.set_position(1, 2)
        tracker._transition_grace = 0

        tracker.process_ctc_result(
            CTCResult(characters="كلمات عشوائية تماما لاعلاقة", confidence=0.9)
        )
        assert tracker._consecutive_failures == 1

        tracker.process_ctc_result(
            CTCResult(characters="الحمد لله رب العالمين", confidence=0.9)
        )
        assert tracker._consecutive_failures == 0


class TestRemainingLettersNotSure:
    def test_remaining_letters_are_not_sure(self, tracker):
        tracker.set_position(1, 1)

        tracker.process_ctc_result(
            CTCResult(characters="بسم الله الرحمن الرحيم", confidence=0.9)
        )
        result = tracker.process_ctc_result(
            CTCResult(characters="بسم الله الرحمن الرحيم", confidence=0.9)
        )

        completed = [e for e in result.ayah_events if e.event_type == "ayah.completed"]
        if completed:
            remaining_events = [e for e in result.letter_statuses if e.confidence == 0.5]
            assert len(remaining_events) > 0
            for update in remaining_events[0].updates:
                assert update.status == LetterStatus.NOT_SURE


class TestTemporalSmoothing:
    def test_correct_match_emits_correct_directly(self, tracker):
        tracker.set_position(1, 2)

        result = tracker.process_ctc_result(
            CTCResult(characters="الحمد لله رب العالمين", confidence=0.9)
        )

        if result.letter_statuses:
            statuses = [u.status for u in result.letter_statuses[0].updates]
            correct_count = sum(1 for s in statuses if s == LetterStatus.CORRECT)
            assert correct_count > 0

    def test_mistake_smoothing_uses_votes(self, tracker):
        _locate(tracker)

        for _ in range(CONSECUTIVE_FAILURES_BEFORE_MISTAKE):
            tracker.process_ctc_result(
                CTCResult(characters="كلمات عشوائية تماما لاعلاقة", confidence=0.9)
            )

        result = tracker.process_ctc_result(
            CTCResult(characters="كلمات عشوائية تماما لاعلاقة", confidence=0.9)
        )
        if result.letter_statuses:
            statuses = [u.status for u in result.letter_statuses[0].updates]
            assert any(s == LetterStatus.INCORRECT for s in statuses)


class TestCharMapFromUthmani:
    def test_skips_tashkeel(self):
        uthmani_words = ["بِسْمِ", "ٱللَّهِ"]
        normalized_words = ["بسم", "الله"]
        char_map = _build_uthmani_char_map(uthmani_words, normalized_words)
        assert len(char_map) == 7
        assert char_map[0] == (0, 0)
        assert char_map[2] == (0, 2)
        assert char_map[3] == (1, 0)

    def test_char_map_matches_normalized_length(self, corpus):
        for key, ayah in corpus.ayahs.items():
            assert len(ayah.uthmani_char_map) == len(ayah.normalized_text_no_spaces), (
                f"Mismatch for {key}: map={len(ayah.uthmani_char_map)} "
                f"vs text={len(ayah.normalized_text_no_spaces)}"
            )


class TestFuzzyFindOptimization:
    def test_max_search_range_limits_search(self):
        score, pos, end, _ = RecitationTracker._fuzzy_find(
            "رحيم", "بسماللهالرحمنالرحيم", max_start_range=5
        )
        assert pos < 5

    def test_zero_range_searches_all(self):
        score, pos, end, _ = RecitationTracker._fuzzy_find(
            "رحيم", "بسماللهالرحمنالرحيم", max_start_range=0
        )
        assert score >= 0.9
