import pytest
import torch

from app.transcription.engine_router import EngineRouter
from app.transcription.forced_align import (
    ForcedAlignResult,
    WordBoundary,
    build_word_token_ranges,
    extract_word_boundaries,
    text_to_tokens,
    FRAME_STRIDE_SAMPLES,
)


@pytest.fixture
def mock_vocab():
    return {"ا": 1, "ل": 2, "ح": 3, "م": 4, "د": 5, "ر": 6, "ب": 7, "[PAD]": 0}


class TestTextToTokens:
    def test_known_chars(self, mock_vocab):
        tokens = text_to_tokens("الحمد", mock_vocab)
        assert tokens == [1, 2, 3, 4, 5]

    def test_unknown_chars_skipped(self, mock_vocab):
        tokens = text_to_tokens("الزمن", mock_vocab)
        assert tokens == [1, 2, 4]

    def test_empty_string(self, mock_vocab):
        assert text_to_tokens("", mock_vocab) == []


class TestBuildWordTokenRanges:
    def test_two_words(self, mock_vocab):
        ranges = build_word_token_ranges(["الحمد", "لله"], mock_vocab)
        assert len(ranges) == 2
        assert ranges[0] == (0, 0, 5)
        assert ranges[1] == (1, 5, 7)

    def test_word_with_no_vocab_match(self, mock_vocab):
        ranges = build_word_token_ranges(["xyz"], mock_vocab)
        assert ranges == []


class TestExtractWordBoundaries:
    def test_basic_extraction(self):
        aligned_tokens = torch.tensor([0, 1, 1, 0, 2, 2, 0, 3, 0])
        scores = torch.tensor([0.0, -0.2, -0.1, 0.0, -0.3, -0.4, 0.0, -0.5, 0.0])

        word_ranges = [(0, 0, 2), (1, 2, 3)]

        boundaries = extract_word_boundaries(
            aligned_tokens, scores, word_ranges, blank_id=0,
        )

        assert len(boundaries) == 2
        assert boundaries[0].word_index == 0
        assert boundaries[0].start_frame == 1
        assert boundaries[0].end_frame == 5
        assert boundaries[0].start_sample == 1 * FRAME_STRIDE_SAMPLES
        assert boundaries[0].score > 0.5
        assert boundaries[0].score <= 1.0
        assert boundaries[1].word_index == 1
        assert boundaries[1].start_frame == 7
        assert boundaries[1].score > 0.0

    def test_empty_alignment(self):
        aligned_tokens = torch.tensor([0, 0, 0])
        scores = torch.tensor([0.0, 0.0, 0.0])
        boundaries = extract_word_boundaries(
            aligned_tokens, scores, [(0, 0, 1)], blank_id=0,
        )
        assert boundaries == []


class TestFitWordsToFrames:
    def test_all_words_fit(self, mock_vocab):
        words = ["الحمد", "لله"]
        result = EngineRouter._fit_words_to_frames(words, mock_vocab, num_frames=100)
        assert result == words

    def test_truncates_when_too_long(self, mock_vocab):
        words = ["الحمد", "لله", "رب", "المحمد"]
        result = EngineRouter._fit_words_to_frames(words, mock_vocab, num_frames=8)
        assert len(result) < len(words)
        assert len(result) >= 1

    def test_returns_empty_when_first_word_too_long(self, mock_vocab):
        words = ["الحمدربالمحمد"]
        result = EngineRouter._fit_words_to_frames(words, mock_vocab, num_frames=3)
        assert result == []


class TestForcedAlignResult:
    def test_construction(self):
        wb = WordBoundary(
            word_index=0, start_frame=10, end_frame=20,
            score=0.85, start_sample=3200, end_sample=6400,
        )
        result = ForcedAlignResult(word_boundaries=[wb], total_frames=100)
        assert result.total_frames == 100
        assert len(result.word_boundaries) == 1
        assert result.word_boundaries[0].score == 0.85
