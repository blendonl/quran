import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.quran.corpus import QuranCorpus, QuranAyah, _build_uthmani_char_map
from app.quran.normalizer import normalize, split_words
from app.matching.prefix_index import PrefixIndex
from app.matching.tracker import RecitationTracker, TrackerState, LetterStatus
from app.transcription.ctc_result import CTCResult
from app.transcription.muaalem_result import MuaalemResult, SifaResult


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


def test_char_map_length_matches_no_spaces(corpus):
    ayah = corpus.get_ayah(1, 1)
    assert len(ayah.uthmani_char_map) == len(ayah.normalized_text_no_spaces)


def test_char_map_length_for_all_ayahs(corpus):
    for key, ayah in corpus.ayahs.items():
        assert len(ayah.uthmani_char_map) == len(ayah.normalized_text_no_spaces), (
            f"Mismatch for {key}: map={len(ayah.uthmani_char_map)} "
            f"vs text={len(ayah.normalized_text_no_spaces)}"
        )


def test_char_map_word_indices_are_valid(corpus):
    ayah = corpus.get_ayah(1, 1)
    for word_idx, letter_idx in ayah.uthmani_char_map:
        assert 0 <= word_idx < len(ayah.normalized_words)


def test_build_uthmani_char_map_simple():
    uthmani_words = ["بسم", "الله"]
    normalized_words = ["بسم", "الله"]
    char_map = _build_uthmani_char_map(uthmani_words, normalized_words)
    assert len(char_map) == 7
    assert char_map[0] == (0, 0)
    assert char_map[1] == (0, 1)
    assert char_map[2] == (0, 2)
    assert char_map[3] == (1, 0)
    assert char_map[4] == (1, 1)
    assert char_map[5] == (1, 2)
    assert char_map[6] == (1, 3)


def test_fuzzy_find_returns_matched_indices():
    score, pos, end, matched = RecitationTracker._fuzzy_find(
        "بسم", "بسماللهالرحمنالرحيم"
    )
    assert score >= 0.9
    assert 0 in matched
    assert 1 in matched
    assert 2 in matched


def test_fuzzy_find_gap_produces_missing_indices():
    score, pos, end, matched = RecitationTracker._fuzzy_find(
        "بماله", "بسماللهالرحمنالرحيم"
    )
    assert score > 0.3
    assert 0 in matched
    assert 1 not in matched


def test_letter_status_exact_match_emits_statuses(tracker):
    result = tracker.process_ctc_result(
        CTCResult(characters="الحمد لله رب العالمين", confidence=0.9)
    )

    assert tracker.state == TrackerState.TRACKING
    assert len(result.letter_statuses) > 0

    all_statuses = []
    for event in result.letter_statuses:
        for update in event.updates:
            all_statuses.append(update.status)

    non_incorrect = sum(
        1 for s in all_statuses if s in (LetterStatus.CORRECT, LetterStatus.NOT_SURE)
    )
    assert non_incorrect > 0


def test_letter_status_event_has_correct_ayah_info(tracker):
    result = tracker.process_ctc_result(
        CTCResult(characters="الحمد لله رب العالمين", confidence=0.9)
    )

    assert len(result.letter_statuses) > 0
    event = result.letter_statuses[0]
    assert event.surah_id == 1
    assert event.ayah_number == 2
    assert event.confidence > 0


def test_tracking_emits_letter_statuses(tracker):
    tracker.process_ctc_result(
        CTCResult(characters="الحمد لله رب", confidence=0.9)
    )
    assert tracker.state == TrackerState.TRACKING

    result = tracker.process_ctc_result(
        CTCResult(characters="الحمد لله رب العالمين", confidence=0.9)
    )

    has_letters = len(result.letter_statuses) > 0
    has_positions = len(result.positions) > 0
    assert has_letters or has_positions


def _make_ayah(
    words: list[str],
    surah_id: int = 1,
    ayah_number: int = 1,
) -> QuranAyah:
    char_map = []
    for wi, w in enumerate(words):
        for li in range(len(w)):
            char_map.append((wi, li))

    normalized = [w for w in words]
    return QuranAyah(
        surah_id=surah_id,
        ayah_number=ayah_number,
        text=" ".join(words),
        words=words,
        normalized_words=normalized,
        normalized_text=" ".join(normalized),
        normalized_text_no_spaces="".join(normalized),
        uthmani_char_map=char_map,
    )


def _make_muaalem_tracker(ayah: QuranAyah) -> RecitationTracker:
    corpus = MagicMock(spec=QuranCorpus)
    corpus.get_ayah.return_value = ayah
    prefix_index = MagicMock()
    t = RecitationTracker(corpus, prefix_index)
    t.state = TrackerState.TRACKING
    t.current_ayah = ayah
    t.current_word_index = 0
    t._transition_grace = 0
    t._muaalem_frames_tracked = 3
    return t


def _make_muaalem_result(
    word_phoneme_map: list[dict],
    uthmani_text: str,
    confidences: list[float] | None = None,
) -> MuaalemResult:
    max_sifat = max((w["sifat_end"] for w in word_phoneme_map), default=0)
    if confidences is None:
        confidences = [0.9] * max_sifat
    sifat = [SifaResult(phoneme_group=f"g{i}") for i in range(max_sifat)]

    return MuaalemResult(
        phonemes_text="x" * 20,
        phoneme_groups=[f"g{i}" for i in range(max_sifat)],
        confidences=confidences,
        sifat=sifat,
        ref_phonemes_len=50,
        word_phoneme_map=word_phoneme_map,
        uthmani_text=uthmani_text,
        ref_phonemes="",
        phonetizer_mappings=None,
    )


class TestMuaalemMissingWordFill:
    def test_gap_word_gets_not_sure(self):
        words = ["aaa", "bbb", "ccc", "ddd"]
        ayah = _make_ayah(words)
        t = _make_muaalem_tracker(ayah)

        wmap = [
            {"word_index": 0, "word": "aaa", "phonemes": "ab", "sifat_start": 0, "sifat_end": 2},
            {"word_index": 2, "word": "ccc", "phonemes": "cd", "sifat_start": 2, "sifat_end": 4},
            {"word_index": 3, "word": "ddd", "phonemes": "ef", "sifat_start": 4, "sifat_end": 6},
        ]
        result = _make_muaalem_result(wmap, " ".join(words))
        output = t.process_muaalem_result(result)

        assert output.letter_statuses
        updates = output.letter_statuses[0].updates
        w1 = [u for u in updates if u.word_index == 1]
        assert len(w1) > 0
        assert all(u.status == LetterStatus.NOT_SURE for u in w1)

    def test_no_fill_past_max_confident(self):
        words = ["aaa", "bbb", "ccc"]
        ayah = _make_ayah(words)
        t = _make_muaalem_tracker(ayah)

        wmap = [
            {"word_index": 0, "word": "aaa", "phonemes": "ab", "sifat_start": 0, "sifat_end": 2},
            {"word_index": 1, "word": "bbb", "phonemes": "cd", "sifat_start": 2, "sifat_end": 4},
        ]
        result = _make_muaalem_result(wmap, " ".join(words))
        output = t.process_muaalem_result(result)

        updates = output.letter_statuses[0].updates
        w2 = [u for u in updates if u.word_index == 2]
        assert len(w2) == 0

    def test_all_mapped_words_stay_correct(self):
        words = ["aaa", "bbb"]
        ayah = _make_ayah(words)
        t = _make_muaalem_tracker(ayah)

        wmap = [
            {"word_index": 0, "word": "aaa", "phonemes": "ab", "sifat_start": 0, "sifat_end": 2},
            {"word_index": 1, "word": "bbb", "phonemes": "cd", "sifat_start": 2, "sifat_end": 4},
        ]
        result = _make_muaalem_result(wmap, " ".join(words))
        output = t.process_muaalem_result(result)

        updates = output.letter_statuses[0].updates
        assert all(u.status == LetterStatus.CORRECT for u in updates)


class TestErrorWindowNarrowing:
    def test_early_word_error_filtered(self):
        words = ["aaa", "bbb", "ccc", "ddd", "eee"]
        uthmani = " ".join(words)
        wmap = [
            {"word_index": i, "word": w, "phonemes": "ab", "sifat_start": i * 2, "sifat_end": i * 2 + 2}
            for i, w in enumerate(words)
        ]
        ayah = _make_ayah(words)

        result = MuaalemResult(
            phonemes_text="x" * 20,
            phoneme_groups=["ab"] * 10,
            confidences=[0.9] * 10,
            sifat=[SifaResult(phoneme_group="ab") for _ in range(10)],
            ref_phonemes_len=30,
            word_phoneme_map=wmap,
            uthmani_text=uthmani,
            ref_phonemes="ref",
            phonetizer_mappings={"m": True},
        )

        mock_err = MagicMock()
        mock_err.error_type = "delete"
        mock_err.speech_error_type = "missing"
        mock_err.expected_ph = "a"
        mock_err.preditected_ph = ""
        mock_err.uthmani_pos = (0, 2)
        mock_err.ref_tajweed_rules = []
        mock_err.expected_len = 1
        mock_err.predicted_len = 0

        mock_module = MagicMock()
        mock_module.explain_error = MagicMock(return_value=[mock_err])
        with patch(
            "app.matching.tracker.RecitationTracker._covered_uthmani_range",
            return_value=(0, len(uthmani)),
        ), patch("app.matching.tracker._explain_error", mock_module.explain_error):
            event = RecitationTracker._extract_recitation_errors(result, ayah, max_word_index=4)

        assert event is None

    def test_recent_word_error_kept(self):
        words = ["aaa", "bbb", "ccc", "ddd", "eee"]
        uthmani = " ".join(words)
        wmap = [
            {"word_index": i, "word": w, "phonemes": "ab", "sifat_start": i * 2, "sifat_end": i * 2 + 2}
            for i, w in enumerate(words)
        ]
        ayah = _make_ayah(words)

        result = MuaalemResult(
            phonemes_text="x" * 20,
            phoneme_groups=["ab"] * 10,
            confidences=[0.9] * 10,
            sifat=[SifaResult(phoneme_group="ab") for _ in range(10)],
            ref_phonemes_len=30,
            word_phoneme_map=wmap,
            uthmani_text=uthmani,
            ref_phonemes="ref",
            phonetizer_mappings={"m": True},
        )

        word3_start = uthmani.index("ddd")
        mock_err = MagicMock()
        mock_err.error_type = "replace"
        mock_err.speech_error_type = "substitution"
        mock_err.expected_ph = "a"
        mock_err.preditected_ph = "b"
        mock_err.uthmani_pos = (word3_start, word3_start + 2)
        mock_err.ref_tajweed_rules = []
        mock_err.expected_len = 1
        mock_err.predicted_len = 1

        mock_module = MagicMock()
        mock_module.explain_error = MagicMock(return_value=[mock_err])
        with patch(
            "app.matching.tracker.RecitationTracker._covered_uthmani_range",
            return_value=(0, len(uthmani)),
        ), patch("app.matching.tracker._explain_error", mock_module.explain_error):
            event = RecitationTracker._extract_recitation_errors(result, ayah, max_word_index=4)

        assert event is not None
        assert len(event.errors) == 1


class TestErrorTypeLetterFiltering:
    def _run_with_error_type(self, error_type: str) -> list:
        words = ["aaa", "bbb", "ccc"]
        uthmani = " ".join(words)
        ayah = _make_ayah(words)
        t = _make_muaalem_tracker(ayah)

        wmap = [
            {"word_index": i, "word": w, "phonemes": "ab", "sifat_start": i * 2, "sifat_end": i * 2 + 2}
            for i, w in enumerate(words)
        ]
        result = MuaalemResult(
            phonemes_text="x" * 20,
            phoneme_groups=["ab"] * 6,
            confidences=[0.9] * 6,
            sifat=[SifaResult(phoneme_group="ab") for _ in range(6)],
            ref_phonemes_len=30,
            word_phoneme_map=wmap,
            uthmani_text=uthmani,
            ref_phonemes="ref",
            phonetizer_mappings={"m": True},
        )

        word1_start = uthmani.index("bbb")
        mock_err = MagicMock()
        mock_err.error_type = error_type
        mock_err.speech_error_type = "substitution"
        mock_err.expected_ph = "a"
        mock_err.preditected_ph = "b"
        mock_err.uthmani_pos = (word1_start, word1_start + 3)
        mock_err.ref_tajweed_rules = []
        mock_err.expected_len = 1
        mock_err.predicted_len = 1

        mock_module = MagicMock()
        mock_module.explain_error = MagicMock(return_value=[mock_err])
        with patch(
            "app.matching.tracker.RecitationTracker._covered_uthmani_range",
            return_value=(0, len(uthmani)),
        ), patch("app.matching.tracker._explain_error", mock_module.explain_error):
            output = t.process_muaalem_result(result)

        updates = []
        for ev in output.letter_statuses:
            updates.extend(ev.updates)
        return [u for u in updates if u.word_index == 1]

    def test_tashkeel_error_does_not_mark_incorrect(self):
        w1 = self._run_with_error_type("tashkeel")
        assert len(w1) > 0
        assert all(u.status != LetterStatus.INCORRECT for u in w1)

    def test_tajweed_error_does_not_mark_incorrect(self):
        w1 = self._run_with_error_type("tajweed")
        assert len(w1) > 0
        assert all(u.status != LetterStatus.INCORRECT for u in w1)

    def test_normal_error_marks_incorrect(self):
        w1 = self._run_with_error_type("normal")
        assert len(w1) > 0
        assert all(u.status == LetterStatus.INCORRECT for u in w1)


class TestMuaalemCorrectThreshold:
    def test_confidence_0_65_is_correct(self):
        words = ["aaa", "bbb"]
        ayah = _make_ayah(words)
        t = _make_muaalem_tracker(ayah)

        wmap = [
            {"word_index": 0, "word": "aaa", "phonemes": "ab", "sifat_start": 0, "sifat_end": 2},
            {"word_index": 1, "word": "bbb", "phonemes": "cd", "sifat_start": 2, "sifat_end": 4},
        ]
        result = _make_muaalem_result(wmap, " ".join(words), confidences=[0.65, 0.65, 0.65, 0.65])
        output = t.process_muaalem_result(result)

        updates = output.letter_statuses[0].updates
        assert all(u.status == LetterStatus.CORRECT for u in updates)


class TestCoverageFallbackEmitsNotSure:
    def test_coverage_fallback_emits_not_sure(self):
        words = ["aaa", "bbb", "ccc", "ddd"]
        ayah = _make_ayah(words)
        t = _make_muaalem_tracker(ayah)

        result = MuaalemResult(
            phonemes_text="x" * 30,
            phoneme_groups=["g0"] * 4,
            confidences=[0.7, 0.7, 0.7, 0.7],
            sifat=[SifaResult(phoneme_group="g0") for _ in range(4)],
            ref_phonemes_len=40,
            word_phoneme_map=None,
            uthmani_text=" ".join(words),
            ref_phonemes="",
            phonetizer_mappings=None,
        )

        output = t.process_muaalem_result(result)

        assert output.letter_statuses
        updates = output.letter_statuses[0].updates
        assert all(u.status == LetterStatus.NOT_SURE for u in updates)
        covered_words = {u.word_index for u in updates}
        assert len(covered_words) > 0

    def test_coverage_fallback_no_letters_below_threshold(self):
        words = ["aaa", "bbb", "ccc"]
        ayah = _make_ayah(words)
        t = _make_muaalem_tracker(ayah)

        result = MuaalemResult(
            phonemes_text="x" * 20,
            phoneme_groups=["g0"] * 3,
            confidences=[0.3, 0.3, 0.3],
            sifat=[SifaResult(phoneme_group="g0") for _ in range(3)],
            ref_phonemes_len=40,
            word_phoneme_map=None,
            uthmani_text=" ".join(words),
            ref_phonemes="",
            phonetizer_mappings=None,
        )

        output = t.process_muaalem_result(result)

        assert len(output.letter_statuses) == 0


class TestThreshold055IsCorrect:
    def test_confidence_0_55_is_correct(self):
        words = ["aaa", "bbb"]
        ayah = _make_ayah(words)
        t = _make_muaalem_tracker(ayah)

        wmap = [
            {"word_index": 0, "word": "aaa", "phonemes": "ab", "sifat_start": 0, "sifat_end": 2},
            {"word_index": 1, "word": "bbb", "phonemes": "cd", "sifat_start": 2, "sifat_end": 4},
        ]
        result = _make_muaalem_result(wmap, " ".join(words), confidences=[0.55, 0.55, 0.55, 0.55])
        output = t.process_muaalem_result(result)

        updates = output.letter_statuses[0].updates
        assert all(u.status == LetterStatus.CORRECT for u in updates)

    def test_confidence_0_54_has_no_correct(self):
        words = ["aaa", "bbb"]
        ayah = _make_ayah(words)
        t = _make_muaalem_tracker(ayah)

        wmap = [
            {"word_index": 0, "word": "aaa", "phonemes": "ab", "sifat_start": 0, "sifat_end": 2},
            {"word_index": 1, "word": "bbb", "phonemes": "cd", "sifat_start": 2, "sifat_end": 4},
        ]
        result = _make_muaalem_result(wmap, " ".join(words), confidences=[0.54, 0.54, 0.54, 0.54])
        output = t.process_muaalem_result(result)

        all_updates = [u for ev in output.letter_statuses for u in ev.updates]
        assert all(u.status != LetterStatus.CORRECT for u in all_updates)


class TestEmitIntervalFormula:
    def test_cap_at_half_second(self):
        new_interval = max(0.25, min(1.0 * 1.1, 0.5))
        assert new_interval == 0.5

    def test_scales_moderately(self):
        new_interval = max(0.25, min(0.3 * 1.1, 0.5))
        assert abs(new_interval - 0.33) < 0.01

    def test_floor_at_quarter_second(self):
        new_interval = max(0.25, min(0.1 * 1.1, 0.5))
        assert new_interval == 0.25
