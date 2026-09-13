from unittest.mock import patch, MagicMock

import numpy as np

from app.transcription.audio_buffer import AudioBuffer


def _make_pcm_silence(num_samples: int) -> bytes:
    return b"\x00" * (num_samples * 2)


def _make_pcm_tone(num_samples: int, frequency: float = 440.0, sample_rate: int = 16000) -> bytes:
    t = np.arange(num_samples) / sample_rate
    samples = (np.sin(2 * np.pi * frequency * t) * 16000).astype(np.int16)
    return samples.tobytes()


def _make_buffer(**kwargs) -> AudioBuffer:
    mock_model = MagicMock()
    mock_model.reset_states = MagicMock()
    with patch("app.transcription.audio_buffer.load_silero_vad", return_value=mock_model):
        return AudioBuffer(**kwargs)


def _patch_speech(has_speech: bool):
    return patch.object(AudioBuffer, "_chunk_has_speech", return_value=has_speech)


def test_no_emit_before_interval():
    buffer = _make_buffer(sample_rate=16000, max_buffer_s=5.0, emit_interval_s=0.5)
    small_chunk = _make_pcm_silence(2000)
    result = buffer.add_audio(small_chunk)
    assert result is None


def test_emits_after_interval():
    buffer = _make_buffer(sample_rate=16000, max_buffer_s=5.0, emit_interval_s=0.5)
    tone = _make_pcm_tone(8000)
    with _patch_speech(True):
        result = buffer.add_audio(tone)
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert len(result) == 8000


def test_buffer_trims_to_max():
    buffer = _make_buffer(sample_rate=16000, max_buffer_s=1.0, emit_interval_s=0.5)
    tone = _make_pcm_tone(8000)
    with _patch_speech(True):
        buffer.add_audio(tone)

    tone2 = _make_pcm_tone(8000)
    with _patch_speech(True):
        result = buffer.add_audio(tone2)

    max_samples = int(1.0 * 16000)
    assert result is not None
    assert len(result) == max_samples


def test_silence_returns_none():
    buffer = _make_buffer(sample_rate=16000, max_buffer_s=5.0, emit_interval_s=0.5)
    silence = _make_pcm_silence(8000)
    result = buffer.add_audio(silence)
    assert result is None


def test_reset_clears_state():
    buffer = _make_buffer(sample_rate=16000, max_buffer_s=5.0, emit_interval_s=0.5)
    with _patch_speech(True):
        buffer.add_audio(_make_pcm_tone(4000))
    buffer.reset()
    assert len(buffer.committed) == 0
    assert buffer.pending_bytes == 0


def test_multiple_small_adds_accumulate():
    buffer = _make_buffer(sample_rate=16000, max_buffer_s=5.0, emit_interval_s=0.5)
    chunk = _make_pcm_tone(2000)

    with _patch_speech(True):
        result = buffer.add_audio(chunk)
        assert result is None

        result = buffer.add_audio(chunk)
        assert result is None

        result = buffer.add_audio(chunk)
        assert result is None

        result = buffer.add_audio(chunk)
        assert result is not None
        assert len(result) == 8000
