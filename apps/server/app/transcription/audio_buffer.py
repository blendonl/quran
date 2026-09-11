import logging

import numpy as np
import torch
from silero_vad import load_silero_vad

from app.config import settings

logger = logging.getLogger(__name__)

BYTES_PER_SAMPLE = 2
SILERO_CHUNK_SAMPLES = 512


class AudioBuffer:
    def __init__(
        self,
        sample_rate: int = settings.audio_sample_rate,
        max_buffer_s: float = settings.audio_max_buffer_s,
        emit_interval_s: float = settings.audio_emit_interval_s,
    ):
        self.sample_rate = sample_rate
        self.max_buffer_bytes = int(max_buffer_s * sample_rate * BYTES_PER_SAMPLE)
        self.emit_interval_bytes = int(emit_interval_s * sample_rate * BYTES_PER_SAMPLE)

        self.committed = bytearray()
        self.pending = bytearray()
        self.pending_bytes = 0

        self._vad_model = load_silero_vad(onnx=True)
        self.trim_on_silence: bool = True
        self.silence_detected: bool = False
        self._silence_chunks = 0
        self._needs_recovery = False
        self._speech_recovery_bytes = 0

    def add_audio(self, pcm_data: bytes) -> np.ndarray | None:
        self.pending.extend(pcm_data)
        self.pending_bytes += len(pcm_data)

        if self.pending_bytes < self.emit_interval_bytes:
            return None

        self.pending_bytes = 0
        chunk = self.pending
        self.pending = bytearray()

        if not self._chunk_has_speech(chunk):
            self._silence_chunks += 1
            if self.trim_on_silence and self._silence_chunks >= settings.silence_reset_chunks:
                keep_bytes = int(1.0 * self.sample_rate * BYTES_PER_SAMPLE)
                old_len = len(self.committed)
                if old_len > keep_bytes:
                    self.committed = self.committed[-keep_bytes:]
                    logger.debug(
                        "Audio trimmed on silence: %d -> %d bytes (silence_chunks=%d)",
                        old_len, len(self.committed), self._silence_chunks,
                    )
                self._needs_recovery = True
                self._speech_recovery_bytes = 0
                self.silence_detected = True
            return None

        if self._silence_chunks >= settings.silence_reset_chunks // 2:
            self._silence_chunks = max(0, self._silence_chunks - 2)
        else:
            self._silence_chunks = 0
        self.committed.extend(chunk)
        self._trim_committed()

        if self._needs_recovery:
            self._speech_recovery_bytes += len(chunk)
            min_recovery_bytes = int(0.3 * self.sample_rate * BYTES_PER_SAMPLE)
            if self._speech_recovery_bytes < min_recovery_bytes:
                logger.debug(
                    "Audio recovery: %d/%d bytes",
                    self._speech_recovery_bytes, min_recovery_bytes,
                )
                return None
            logger.debug("Audio recovery complete")
            self._needs_recovery = False
            self._speech_recovery_bytes = 0

        snapshot = np.frombuffer(self.committed, dtype=np.int16).copy().astype(np.float32)
        snapshot /= 32768.0
        return snapshot

    def _chunk_has_speech(self, chunk: bytearray | bytes) -> bool:
        samples = np.frombuffer(chunk, dtype=np.int16)
        rms = np.sqrt(np.mean((samples.astype(np.float32) / 32768.0) ** 2))
        if rms < settings.audio_energy_threshold:
            return False

        audio_float = samples.astype(np.float32) / 32768.0
        tensor = torch.from_numpy(audio_float)

        max_prob = 0.0
        for start in range(0, len(tensor), SILERO_CHUNK_SAMPLES):
            window = tensor[start:start + SILERO_CHUNK_SAMPLES]
            if len(window) < SILERO_CHUNK_SAMPLES:
                padded = torch.zeros(SILERO_CHUNK_SAMPLES)
                padded[:len(window)] = window
                window = padded
            prob = self._vad_model(window, self.sample_rate).item()
            max_prob = max(max_prob, prob)
            if prob >= settings.vad_threshold:
                return True

        if max_prob > 0:
            logger.debug("Silero VAD: max_prob=%.3f threshold=%.2f (rms=%.4f)",
                         max_prob, settings.vad_threshold, rms)
        return False

    def _trim_committed(self):
        if len(self.committed) > self.max_buffer_bytes:
            self.committed = self.committed[-self.max_buffer_bytes:]

    def trim_to_recent(self, seconds: float):
        keep_bytes = int(seconds * self.sample_rate * BYTES_PER_SAMPLE)
        if len(self.committed) > keep_bytes:
            self.committed = self.committed[-keep_bytes:]

    def set_recovery_mode(self):
        self._needs_recovery = True
        self._speech_recovery_bytes = 0

    @property
    def total_samples(self) -> int:
        return len(self.committed) // BYTES_PER_SAMPLE

    def get_audio_range(self, start_sample: int, end_sample: int) -> np.ndarray | None:
        start_byte = start_sample * BYTES_PER_SAMPLE
        end_byte = end_sample * BYTES_PER_SAMPLE
        start_byte = max(0, start_byte)
        end_byte = min(end_byte, len(self.committed))
        if end_byte <= start_byte or (end_byte - start_byte) < BYTES_PER_SAMPLE:
            return None
        data = self.committed[start_byte:end_byte]
        return np.frombuffer(data, dtype=np.int16).copy().astype(np.float32) / 32768.0

    def get_audio_from_sample(self, start_sample: int) -> np.ndarray | None:
        start_byte = start_sample * BYTES_PER_SAMPLE
        if start_byte >= len(self.committed):
            return None
        start_byte = max(0, start_byte)
        data = self.committed[start_byte:]
        if len(data) < BYTES_PER_SAMPLE:
            return None
        return np.frombuffer(data, dtype=np.int16).copy().astype(np.float32) / 32768.0

    def get_full_audio(self) -> np.ndarray | None:
        if len(self.committed) < BYTES_PER_SAMPLE:
            return None
        return np.frombuffer(self.committed, dtype=np.int16).copy().astype(np.float32) / 32768.0

    def reset(self):
        self.committed = bytearray()
        self.pending = bytearray()
        self.pending_bytes = 0
        self._silence_chunks = 0
        self._needs_recovery = False
        self._speech_recovery_bytes = 0
        self.silence_detected = False
        self._vad_model.reset_states()
