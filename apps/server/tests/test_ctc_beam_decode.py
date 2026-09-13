import math
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

try:
    from app.transcription.ctc_engine import CTCEngine
except ImportError:
    CTCEngine = None

from app.transcription.ctc_result import CTCResult

pytestmark = pytest.mark.skipif(CTCEngine is None, reason="transformers not installed")


def _make_engine(**kwargs):
    with patch.object(CTCEngine, "__init__", lambda self, **kw: None):
        engine = CTCEngine()
        engine.device = "cpu"
        engine.dtype = torch.float32
        engine.model_name = "test"
        engine.decode_mode = kwargs.get("decode_mode", "beam")
        engine.processor = MagicMock()
        engine.processor.tokenizer.pad_token_id = 0
        engine.model = MagicMock()
        engine.beam_decoder = kwargs.get("beam_decoder", None)
        engine._load_lock = MagicMock()
        return engine


class TestDecodeGreedy:
    def test_returns_ctc_result(self):
        engine = _make_engine(decode_mode="greedy")
        logits = torch.randn(1, 10, 32)

        predicted_ids = torch.argmax(logits, dim=-1)
        engine.processor.batch_decode.return_value = ["بسم"]
        engine.processor.tokenizer.pad_token_id = 0

        with patch("app.transcription.ctc_engine.settings") as mock_settings:
            mock_settings.ctc_confidence_threshold = 0.0
            result = engine._decode_greedy(logits)

        assert isinstance(result, CTCResult)
        assert result.characters == "بسم"

    def test_returns_none_for_empty(self):
        engine = _make_engine(decode_mode="greedy")
        logits = torch.randn(1, 10, 32)

        engine.processor.batch_decode.return_value = [""]

        with patch("app.transcription.ctc_engine.settings") as mock_settings:
            mock_settings.ctc_confidence_threshold = 0.0
            result = engine._decode_greedy(logits)

        assert result is None


class TestDecodeBeam:
    def test_returns_ctc_result(self):
        beam_decoder = MagicMock()
        beam_decoder.decode_beams.return_value = [
            ("بسم الله", None, None, -2.0, None),
        ]
        engine = _make_engine(beam_decoder=beam_decoder)

        logits = torch.randn(1, 10, 32)

        with patch("app.transcription.ctc_engine.settings") as mock_settings:
            mock_settings.ctc_confidence_threshold = 0.0
            mock_settings.ctc_beam_width = 10
            mock_settings.ctc_beam_prune_logp = -10.0
            mock_settings.ctc_beam_token_min_logp = -5.0
            result = engine._decode_beam(logits)

        assert isinstance(result, CTCResult)
        assert result.characters == "بسم الله"
        expected_confidence = math.exp(-2.0 / len("بسم الله"))
        assert abs(result.confidence - expected_confidence) < 1e-6

    def test_falls_back_to_greedy_on_empty_beams(self):
        beam_decoder = MagicMock()
        beam_decoder.decode_beams.return_value = []
        engine = _make_engine(beam_decoder=beam_decoder)

        logits = torch.randn(1, 10, 32)

        with patch.object(engine, "_decode_greedy", return_value=CTCResult("فال", 0.5)) as mock_greedy:
            result = engine._decode_beam(logits)

        mock_greedy.assert_called_once_with(logits)
        assert result.characters == "فال"

    def test_falls_back_to_greedy_on_empty_text(self):
        beam_decoder = MagicMock()
        beam_decoder.decode_beams.return_value = [
            ("", None, None, -1.0, None),
        ]
        engine = _make_engine(beam_decoder=beam_decoder)

        logits = torch.randn(1, 10, 32)

        with patch.object(engine, "_decode_greedy", return_value=CTCResult("ب", 0.5)) as mock_greedy:
            result = engine._decode_beam(logits)

        mock_greedy.assert_called_once_with(logits)

    def test_below_confidence_threshold_returns_none(self):
        beam_decoder = MagicMock()
        beam_decoder.decode_beams.return_value = [
            ("بسم", None, None, -100.0, None),
        ]
        engine = _make_engine(beam_decoder=beam_decoder)

        logits = torch.randn(1, 10, 32)

        with patch("app.transcription.ctc_engine.settings") as mock_settings:
            mock_settings.ctc_confidence_threshold = 0.99
            mock_settings.ctc_beam_width = 10
            mock_settings.ctc_beam_prune_logp = -10.0
            mock_settings.ctc_beam_token_min_logp = -5.0
            result = engine._decode_beam(logits)

        assert result is None


class TestTranscribeSyncDispatch:
    def test_uses_beam_when_available(self):
        engine = _make_engine(decode_mode="beam", beam_decoder=MagicMock())
        engine.processor.return_value = MagicMock(
            input_values=torch.randn(1, 16000)
        )
        engine.model.return_value = MagicMock(logits=torch.randn(1, 10, 32))

        with (
            patch.object(engine, "_decode_beam", return_value=CTCResult("بسم", 0.9)) as mock_beam,
            patch.object(engine, "_decode_greedy") as mock_greedy,
        ):
            result = engine._transcribe_sync(np.zeros(16000, dtype=np.float32))

        mock_beam.assert_called_once()
        mock_greedy.assert_not_called()
        assert result.characters == "بسم"

    def test_falls_back_to_greedy_when_no_decoder(self):
        engine = _make_engine(decode_mode="beam", beam_decoder=None)
        engine.processor.return_value = MagicMock(
            input_values=torch.randn(1, 16000)
        )
        engine.model.return_value = MagicMock(logits=torch.randn(1, 10, 32))

        with (
            patch.object(engine, "_decode_beam") as mock_beam,
            patch.object(engine, "_decode_greedy", return_value=CTCResult("بسم", 0.9)) as mock_greedy,
        ):
            result = engine._transcribe_sync(np.zeros(16000, dtype=np.float32))

        mock_beam.assert_not_called()
        mock_greedy.assert_called_once()

    def test_greedy_mode_skips_beam(self):
        engine = _make_engine(decode_mode="greedy", beam_decoder=MagicMock())
        engine.processor.return_value = MagicMock(
            input_values=torch.randn(1, 16000)
        )
        engine.model.return_value = MagicMock(logits=torch.randn(1, 10, 32))

        with (
            patch.object(engine, "_decode_beam") as mock_beam,
            patch.object(engine, "_decode_greedy", return_value=CTCResult("بسم", 0.9)) as mock_greedy,
        ):
            result = engine._transcribe_sync(np.zeros(16000, dtype=np.float32))

        mock_beam.assert_not_called()
        mock_greedy.assert_called_once()
