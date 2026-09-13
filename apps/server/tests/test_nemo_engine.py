from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.transcription.ctc_result import CTCResult


@pytest.fixture
def nemo_engine():
    with patch("app.transcription.nemo_engine.resolve_model_path", return_value="test"):
        from app.transcription.nemo_engine import NemoCtcEngine

        with patch.object(NemoCtcEngine, "__init__", lambda self, **kw: None):
            engine = NemoCtcEngine()
            engine.device = "cpu"
            engine.model_name = "test"
            engine.model = MagicMock()
            engine._load_lock = MagicMock()
            return engine


class TestNemoTranscribeSync:
    def test_returns_ctc_result(self, nemo_engine):
        mock_output = [MagicMock(text="بسم الله", score=-1.0)]
        nemo_engine.model.transcribe.return_value = mock_output

        with patch("app.transcription.nemo_engine.settings") as mock_settings:
            mock_settings.ctc_confidence_threshold = 0.0
            result = nemo_engine._transcribe_sync(np.zeros(16000, dtype=np.float32))

        assert isinstance(result, CTCResult)
        assert result.characters == "بسم الله"

    def test_returns_none_for_empty_output(self, nemo_engine):
        nemo_engine.model.transcribe.return_value = []

        result = nemo_engine._transcribe_sync(np.zeros(16000, dtype=np.float32))
        assert result is None

    def test_returns_none_for_empty_text(self, nemo_engine):
        mock_output = [MagicMock(text="")]
        nemo_engine.model.transcribe.return_value = mock_output

        result = nemo_engine._transcribe_sync(np.zeros(16000, dtype=np.float32))
        assert result is None

    def test_below_confidence_returns_none(self, nemo_engine):
        mock_output = [MagicMock(text="بسم", score=-100.0)]
        nemo_engine.model.transcribe.return_value = mock_output

        with patch("app.transcription.nemo_engine.settings") as mock_settings:
            mock_settings.ctc_confidence_threshold = 0.5
            result = nemo_engine._transcribe_sync(np.zeros(16000, dtype=np.float32))

        assert result is None
