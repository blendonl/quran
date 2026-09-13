import json
import tempfile
from pathlib import Path

import pytest

from app.quran.corpus import QuranCorpus
from app.matching.prefix_index import PrefixIndex
from app.matching.tracker import RecitationTracker, TrackerState
from app.transcription.ctc_result import CTCResult
from app.transcription.forced_align import ForcedAlignResult, WordBoundary
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


def _set_tracking(tracker, surah_id=1, ayah_number=1):
    output = tracker.set_position(surah_id, ayah_number)
    assert tracker.state == TrackerState.TRACKING
    return output


class TestProcessForcedAlignResult:
    def test_forward_only_confirmation(self, tracker):
        _set_tracking(tracker)
        boundaries = [
            WordBoundary(word_index=0, start_frame=0, end_frame=10, score=0.8, start_sample=0, end_sample=3200),
            WordBoundary(word_index=1, start_frame=11, end_frame=20, score=0.7, start_sample=3520, end_sample=6400),
        ]
        result = ForcedAlignResult(word_boundaries=boundaries, total_frames=50)
        output = tracker.process_forced_align_result(result)

        assert len(output.word_statuses) == 1
        updates = output.word_statuses[0].updates
        assert len(updates) == 2
        assert all(u.status == "ALIGNED" for u in updates)
        assert tracker._confirmed_word_index == 1

    def test_no_retreat(self, tracker):
        _set_tracking(tracker)
        boundaries_1 = [
            WordBoundary(word_index=0, start_frame=0, end_frame=10, score=0.8, start_sample=0, end_sample=3200),
            WordBoundary(word_index=1, start_frame=11, end_frame=20, score=0.7, start_sample=3520, end_sample=6400),
            WordBoundary(word_index=2, start_frame=21, end_frame=30, score=0.6, start_sample=6720, end_sample=9600),
        ]
        tracker.process_forced_align_result(ForcedAlignResult(word_boundaries=boundaries_1, total_frames=50))
        assert tracker._confirmed_word_index == 2

        boundaries_2 = [
            WordBoundary(word_index=0, start_frame=0, end_frame=10, score=0.9, start_sample=0, end_sample=3200),
            WordBoundary(word_index=1, start_frame=11, end_frame=20, score=0.9, start_sample=3520, end_sample=6400),
        ]
        output = tracker.process_forced_align_result(ForcedAlignResult(word_boundaries=boundaries_2, total_frames=50))
        assert tracker._confirmed_word_index == 2
        assert len(output.word_statuses) == 0

    def test_position_event_emitted(self, tracker):
        _set_tracking(tracker)
        boundaries = [
            WordBoundary(word_index=0, start_frame=0, end_frame=10, score=0.8, start_sample=0, end_sample=3200),
            WordBoundary(word_index=1, start_frame=11, end_frame=20, score=0.7, start_sample=3520, end_sample=6400),
        ]
        output = tracker.process_forced_align_result(ForcedAlignResult(word_boundaries=boundaries, total_frames=50))
        assert len(output.positions) == 1
        assert output.positions[0].word_index == 1

    def test_low_score_words_skipped(self, tracker):
        _set_tracking(tracker)
        boundaries = [
            WordBoundary(word_index=0, start_frame=0, end_frame=10, score=0.1, start_sample=0, end_sample=3200),
        ]
        output = tracker.process_forced_align_result(ForcedAlignResult(word_boundaries=boundaries, total_frames=50))
        assert len(output.word_statuses) == 0
        assert tracker._confirmed_word_index == -1

    def test_ayah_completion(self, tracker, corpus):
        _set_tracking(tracker)
        ayah = tracker.current_ayah
        total_words = len(ayah.normalized_words)

        boundaries = [
            WordBoundary(
                word_index=i, start_frame=i * 10, end_frame=(i + 1) * 10,
                score=0.8, start_sample=i * 3200, end_sample=(i + 1) * 3200,
            )
            for i in range(total_words)
        ]
        output = tracker.process_forced_align_result(
            ForcedAlignResult(word_boundaries=boundaries, total_frames=total_words * 10)
        )
        assert any(e.event_type == "ayah.completed" for e in output.ayah_events)

    def test_not_tracking_returns_empty(self, tracker):
        assert tracker.state == TrackerState.LOCATING
        boundaries = [
            WordBoundary(word_index=0, start_frame=0, end_frame=10, score=0.8, start_sample=0, end_sample=3200),
        ]
        output = tracker.process_forced_align_result(ForcedAlignResult(word_boundaries=boundaries, total_frames=50))
        assert len(output.positions) == 0
        assert len(output.word_statuses) == 0


class TestProcessAyahMuaalemResult:
    def _make_muaalem_result(self, word_count=4):
        return MuaalemResult(
            phonemes_text="b i s m a l l a h",
            phoneme_groups=["b", "i", "s", "m"] * word_count,
            confidences=[0.8] * (word_count * 4),
            sifat=[
                SifaResult(phoneme_group=g) for g in (["b", "i", "s", "m"] * word_count)
            ],
            ref_phonemes_len=word_count * 4,
            word_phoneme_map=[
                {"word_index": i, "sifat_start": i * 4, "sifat_end": (i + 1) * 4}
                for i in range(word_count)
            ],
            uthmani_text="بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
        )

    def test_word_status_events(self, tracker):
        _set_tracking(tracker)
        result = self._make_muaalem_result()
        output = tracker.process_ayah_muaalem_result(result)

        assert len(output.word_statuses) == 1
        updates = output.word_statuses[0].updates
        assert len(updates) == 4
        assert all(u.status == "CORRECT" for u in updates)

    def test_letter_status_backward_compat(self, tracker):
        _set_tracking(tracker)
        result = self._make_muaalem_result()
        output = tracker.process_ayah_muaalem_result(result)
        assert len(output.letter_statuses) >= 1
