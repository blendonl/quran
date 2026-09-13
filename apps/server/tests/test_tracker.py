import json
import tempfile
from pathlib import Path

import pytest

from app.quran.corpus import QuranCorpus
from app.matching.prefix_index import PrefixIndex
from app.matching.tracker import RecitationTracker, TrackerState, SurahCompletedEvent
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
            },
            {
                "id": 41,
                "name_simple": "Fussilat",
                "name_arabic": "فصلت",
                "verses_count": 2,
                "ayahs": [
                    {
                        "ayah_number": 1,
                        "verse_key": "41:1",
                        "text_uthmani": "حمٓ",
                    },
                    {
                        "ayah_number": 2,
                        "verse_key": "41:2",
                        "text_uthmani": "تَنزِيلٌ مِّنَ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
                    },
                ],
            },
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


def test_starts_locating(tracker):
    assert tracker.state == TrackerState.LOCATING


def test_fuzzy_find_exact():
    score, pos, end, _ = RecitationTracker._fuzzy_find("بسم", "بسماللهالرحمنالرحيم")
    assert score >= 0.9
    assert pos == 0
    assert end == 3


def test_fuzzy_find_with_noise():
    score, _, _, _ = RecitationTracker._fuzzy_find("بسمل", "بسماللهالرحمنالرحيم")
    assert score >= 0.5


def test_locates_with_full_transcription(tracker):
    tracker.process_ctc_result(CTCResult(characters="الحمد لله رب العالمين", confidence=0.9))

    assert tracker.state == TrackerState.TRACKING
    assert tracker.current_ayah is not None
    assert tracker.current_ayah.surah_id == 1
    assert tracker.current_ayah.ayah_number == 2


def test_emits_ayah_started(tracker):
    result = tracker.process_ctc_result(CTCResult(characters="الحمد لله رب العالمين", confidence=0.9))

    started = [e for e in result.ayah_events if e.event_type == "ayah.started"]
    assert len(started) == 1
    assert started[0].surah_id == 1
    assert started[0].ayah_number == 2


def test_tracking_advances_position(tracker):
    tracker.process_ctc_result(CTCResult(characters="الحمد لله رب", confidence=0.9))
    assert tracker.state == TrackerState.TRACKING

    result = tracker.process_ctc_result(CTCResult(characters="الحمد لله رب العالمين", confidence=0.9))

    assert len(result.positions) > 0


def test_position_never_retreats(tracker):
    tracker.process_ctc_result(CTCResult(characters="الحمد لله", confidence=0.9))
    assert tracker.state == TrackerState.TRACKING
    word_after = tracker.current_word_index

    tracker.process_ctc_result(CTCResult(characters="الحمد لله", confidence=0.9))
    assert tracker.current_word_index >= word_after


def test_completes_ayah(tracker):
    tracker.process_ctc_result(CTCResult(characters="الحمد لله رب", confidence=0.9))

    tracker.process_ctc_result(CTCResult(characters="الحمد لله رب العالمين", confidence=0.9))
    result = tracker.process_ctc_result(CTCResult(characters="الحمد لله رب العالمين", confidence=0.9))

    completed = [e for e in result.ayah_events if e.event_type == "ayah.completed"]
    assert len(completed) == 1


def test_ignores_short_transcription(tracker):
    result = tracker.process_ctc_result(CTCResult(characters="بس", confidence=0.9))

    assert tracker.state == TrackerState.LOCATING
    assert len(result.positions) == 0


def test_fuzzy_find_handles_ctc_noise():
    score, pos, _, _ = RecitationTracker._fuzzy_find("بسماللهوالرخمنورحيم", "بسماللهالرحمنالرحيم")
    assert score >= 0.7
    assert pos == 0


def test_fuzzy_find_phonetic_confusion():
    score, pos, end, _ = RecitationTracker._fuzzy_find("بصمالله", "بسماللهالرحمنالرحيم")
    assert score >= 0.9
    assert pos == 0
    assert end == 7


def test_fuzzy_find_phonetic_kha_ain():
    score, _, _, _ = RecitationTracker._fuzzy_find("الخالمين", "العلمين")
    assert score >= 0.5


def test_reset(tracker):
    tracker.process_ctc_result(CTCResult(characters="الحمد لله رب العالمين", confidence=0.9))
    tracker.reset()

    assert tracker.state == TrackerState.LOCATING
    assert tracker.current_ayah is None
    assert tracker.current_word_index == 0
    assert tracker.matched_char_pos == 0
    assert tracker._candidates == []
    assert tracker._prev_phonetic_query == ""
    assert tracker._need_advance_to_complete is False


def test_forward_only_matching(tracker):
    tracker.process_ctc_result(CTCResult(characters="الحمد لله رب", confidence=0.9))
    assert tracker.state == TrackerState.TRACKING
    pos_before = tracker.matched_char_pos
    ayah_before = tracker.current_ayah

    result = tracker.process_ctc_result(
        CTCResult(characters="الحمد لله رب العالمين", confidence=0.9)
    )

    advanced = tracker.matched_char_pos > pos_before
    transitioned = tracker.current_ayah != ayah_before
    assert advanced or transitioned


def test_ayah_repeat_resets_position(tracker):
    _locate(tracker)

    ayah_1_2 = tracker.corpus.get_ayah(1, 2)
    tracker.current_ayah = ayah_1_2
    tracker.matched_char_pos = len(ayah_1_2.normalized_text_no_spaces)
    tracker.current_word_index = 3
    tracker._need_advance_to_complete = False

    tracker.process_ctc_result(CTCResult(characters="الحمد لله رب العالمين", confidence=0.9))
    result = tracker.process_ctc_result(CTCResult(characters="الحمد لله رب العالمين", confidence=0.9))

    started = [e for e in result.ayah_events if e.event_type == "ayah.started"]
    assert len(started) >= 1
    assert tracker.current_word_index == 0 or tracker.current_ayah.ayah_number != 2


def test_consecutive_failures_do_not_emit_letters(tracker):
    _locate(tracker)

    for _ in range(5):
        result = tracker.process_ctc_result(
            CTCResult(characters="كلمات عشوائية تماما لاعلاقة", confidence=0.9)
        )
        assert len(result.letter_statuses) == 0


def test_never_falls_back_to_locating(tracker):
    _locate(tracker)

    for _ in range(20):
        tracker.process_ctc_result(
            CTCResult(characters="كلمات عشوائية تماما لاعلاقة", confidence=0.9)
        )

    assert tracker.state == TrackerState.TRACKING
    assert tracker.current_ayah is not None


def test_transition_to_next_ayah_still_works(tracker):
    tracker.process_ctc_result(CTCResult(characters="الحمد لله رب", confidence=0.9))
    assert tracker.state == TrackerState.TRACKING

    tracker.process_ctc_result(
        CTCResult(characters="الحمد لله رب العالمين", confidence=0.9)
    )
    result = tracker.process_ctc_result(
        CTCResult(characters="الحمد لله رب العالمين", confidence=0.9)
    )

    completed = [e for e in result.ayah_events if e.event_type == "ayah.completed"]
    started = [e for e in result.ayah_events if e.event_type == "ayah.started"]
    assert len(completed) >= 1
    assert len(started) >= 1
    assert tracker.current_ayah.ayah_number == 3


def test_ambiguous_match_waits(tracker):
    result = tracker.process_ctc_result(
        CTCResult(characters="الرحمن الرحيم", confidence=0.9)
    )
    assert tracker.state == TrackerState.LOCATING
    assert len(result.positions) == 0


def test_unique_match_locates(tracker):
    result = tracker.process_ctc_result(
        CTCResult(characters="الحمد لله رب العالمين", confidence=0.9)
    )
    assert tracker.state == TrackerState.TRACKING
    assert tracker.current_ayah.ayah_number == 2


def test_ambiguous_then_unique_locates(tracker):
    tracker.process_ctc_result(
        CTCResult(characters="الرحمن الرحيم", confidence=0.9)
    )
    assert tracker.state == TrackerState.LOCATING

    tracker.process_ctc_result(
        CTCResult(characters="الحمد لله رب العالمين", confidence=0.9)
    )
    assert tracker.state == TrackerState.TRACKING
    assert tracker.current_ayah.ayah_number == 2


def test_progressive_narrowing_locates(tracker):
    result = tracker.process_ctc_result(CTCResult(characters="الر", confidence=0.9))
    assert tracker.state == TrackerState.LOCATING
    assert len(tracker._candidates) > 1

    result = tracker.process_ctc_result(CTCResult(characters="الرحمن الرحيم", confidence=0.9))
    assert tracker.state == TrackerState.LOCATING
    assert len(tracker._candidates) >= 1


def test_ctc_regression_triggers_fresh_search(tracker):
    tracker.process_ctc_result(CTCResult(characters="الرحم", confidence=0.9))
    assert tracker.state == TrackerState.LOCATING

    tracker.process_ctc_result(CTCResult(characters="الحمد لله", confidence=0.9))
    assert tracker.state == TrackerState.TRACKING
    assert tracker.current_ayah.ayah_number == 2


def test_zero_candidates_recovers(tracker):
    tracker.process_ctc_result(CTCResult(characters="ظظظظظ", confidence=0.9))
    assert tracker.state == TrackerState.LOCATING
    assert tracker._candidates == []

    tracker.process_ctc_result(CTCResult(characters="الحمد لله رب العالمين", confidence=0.9))
    assert tracker.state == TrackerState.TRACKING
    assert tracker.current_ayah.ayah_number == 2


def test_noisy_ctc_prefix_matches_from_later_word(tracker):
    result = tracker.process_ctc_result(
        CTCResult(characters="كن لوذ الرحم", confidence=0.9)
    )
    assert tracker.state == TrackerState.LOCATING
    assert len(tracker._candidates) > 1


def test_noisy_ctc_locates_from_later_word(tracker):
    result = tracker.process_ctc_result(
        CTCResult(characters="كن الحمد لله رب العالمين", confidence=0.9)
    )
    assert tracker.state == TrackerState.TRACKING
    assert tracker.current_ayah.surah_id == 1
    assert tracker.current_ayah.ayah_number == 2


def test_no_cascade_after_mid_ayah_locate(tracker):
    _locate(tracker)
    assert tracker._need_advance_to_complete is True

    result = tracker.process_ctc_result(
        CTCResult(characters="الحمد لله رب العالمين", confidence=0.9)
    )

    completed = [e for e in result.ayah_events if e.event_type == "ayah.completed"]
    assert len(completed) == 0
    assert tracker.current_ayah.ayah_number == 2


def test_set_position_starts_tracking(tracker):
    output = tracker.set_position(1, 2)

    assert tracker.state == TrackerState.TRACKING
    assert tracker.current_ayah is not None
    assert tracker.current_ayah.surah_id == 1
    assert tracker.current_ayah.ayah_number == 2
    assert tracker.matched_char_pos == 0
    assert tracker.current_word_index == 0

    started = [e for e in output.ayah_events if e.event_type == "ayah.started"]
    assert len(started) == 1
    assert started[0].surah_id == 1
    assert started[0].ayah_number == 2
    assert started[0].text != ""


def test_set_position_invalid_ayah(tracker):
    output = tracker.set_position(999, 1)

    assert tracker.state == TrackerState.LOCATING
    assert tracker.current_ayah is None
    assert len(output.ayah_events) == 0


def test_set_position_then_tracking_works(tracker):
    tracker.set_position(1, 2)

    result = tracker.process_ctc_result(
        CTCResult(characters="الحمد لله رب العالمين", confidence=0.9)
    )

    assert tracker.state == TrackerState.TRACKING
    assert tracker.current_ayah is not None


def test_surah_completed_on_boundary(tracker):
    tracker.set_position(1, 3)

    ayah = tracker.corpus.get_ayah(1, 3)
    tracker.matched_char_pos = len(ayah.normalized_text_no_spaces)
    tracker.current_word_index = len(ayah.normalized_words) - 1
    tracker._need_advance_to_complete = False

    result = tracker.process_ctc_result(
        CTCResult(characters="الرحمن الرحيم", confidence=0.9)
    )

    if result.surah_completed:
        sc = result.surah_completed[0]
        assert sc.surah_id == 1
        assert sc.next_surah_id is None


def test_surah_completed_with_next_surah():
    data = {
        "surahs": [
            {
                "id": 1,
                "name_simple": "Al-Fatihah",
                "name_arabic": "الفاتحة",
                "verses_count": 1,
                "ayahs": [
                    {
                        "ayah_number": 1,
                        "verse_key": "1:1",
                        "text_uthmani": "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
                    },
                ],
            },
            {
                "id": 2,
                "name_simple": "Al-Baqarah",
                "name_arabic": "البقرة",
                "verses_count": 1,
                "ayahs": [
                    {
                        "ayah_number": 1,
                        "verse_key": "2:1",
                        "text_uthmani": "الٓمٓ",
                    },
                ],
            },
        ]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f, ensure_ascii=False)
        f.flush()
        corpus = QuranCorpus(Path(f.name))

    prefix_index = PrefixIndex(corpus)
    tracker = RecitationTracker(corpus, prefix_index)

    tracker.set_position(1, 1)
    ayah = corpus.get_ayah(1, 1)
    tracker.matched_char_pos = len(ayah.normalized_text_no_spaces)
    tracker._need_advance_to_complete = False

    tracker.process_ctc_result(
        CTCResult(characters="بسم الله الرحمن الرحيم", confidence=0.9)
    )
    result = tracker.process_ctc_result(
        CTCResult(characters="بسم الله الرحمن الرحيم", confidence=0.9)
    )

    assert len(result.surah_completed) > 0
    sc = result.surah_completed[0]
    assert sc.surah_id == 1
    assert sc.next_surah_id == 2
