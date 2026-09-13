import json
import tempfile
from pathlib import Path

import pytest

from app.matching.muqattaat import is_muqattaat, spelled_out
from app.quran.corpus import QuranCorpus
from app.matching.prefix_index import PrefixIndex
from app.matching.tracker import RecitationTracker, TrackerState
from app.transcription.ctc_result import CTCResult


def test_is_muqattaat_alm():
    assert is_muqattaat("الم") is True


def test_is_muqattaat_hm():
    assert is_muqattaat("حم") is True


def test_is_muqattaat_with_combining_marks():
    assert is_muqattaat("حم\u0653") is True


def test_is_muqattaat_regular_word():
    assert is_muqattaat("الحمد") is False


def test_is_muqattaat_empty():
    assert is_muqattaat("") is False


def test_is_muqattaat_too_long():
    assert is_muqattaat("المصالمر") is False


def test_spelled_out_alm():
    assert spelled_out("الم") == "الفلامميم"


def test_spelled_out_hm():
    assert spelled_out("حم") == "حاميم"


def test_spelled_out_regular_word():
    assert spelled_out("الحمد") is None


@pytest.fixture
def corpus():
    data = {
        "surahs": [
            {
                "id": 2,
                "name_simple": "Al-Baqarah",
                "name_arabic": "البقرة",
                "verses_count": 3,
                "ayahs": [
                    {
                        "ayah_number": 1,
                        "verse_key": "2:1",
                        "text_uthmani": "الٓمٓ",
                    },
                    {
                        "ayah_number": 2,
                        "verse_key": "2:2",
                        "text_uthmani": "ذَٰلِكَ ٱلْكِتَٰبُ لَا رَيْبَ فِيهِ هُدًى لِّلْمُتَّقِينَ",
                    },
                    {
                        "ayah_number": 3,
                        "verse_key": "2:3",
                        "text_uthmani": "ٱلَّذِينَ يُؤْمِنُونَ بِٱلْغَيْبِ",
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


def test_auto_complete_muqattaat_on_locate(tracker):
    result = tracker.process_ctc_result(
        CTCResult(characters="ذلك الكتاب لا ريب فيه", confidence=0.9)
    )

    assert tracker.state == TrackerState.TRACKING
    assert tracker.current_ayah.ayah_number == 2

    started = [e for e in result.ayah_events if e.event_type == "ayah.started"]
    completed = [e for e in result.ayah_events if e.event_type == "ayah.completed"]

    muqattaat_started = [e for e in started if e.ayah_number == 1]
    muqattaat_completed = [e for e in completed if e.ayah_number == 1]
    ayah2_started = [e for e in started if e.ayah_number == 2]

    assert len(muqattaat_started) == 1
    assert len(muqattaat_completed) == 1
    assert len(ayah2_started) == 1


def test_no_auto_complete_for_regular_ayah(tracker):
    result = tracker.process_ctc_result(
        CTCResult(characters="الذين يؤمنون بالغيب", confidence=0.9)
    )

    assert tracker.state == TrackerState.TRACKING
    assert tracker.current_ayah.ayah_number == 3

    completed = [e for e in result.ayah_events if e.event_type == "ayah.completed"]
    assert len(completed) == 0
