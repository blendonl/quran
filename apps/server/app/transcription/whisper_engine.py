import asyncio
import logging

import numpy as np

from app.config import resolve_model_path, settings
from app.transcription.ctc_result import CTCResult

logger = logging.getLogger(__name__)


class WhisperEngine:
    def __init__(
        self,
        model_name: str = settings.whisper_model,
        device: str = settings.whisper_device,
        compute_type: str = settings.whisper_compute_type,
        beam_size: int = settings.whisper_beam_size,
        confidence_threshold: float = settings.whisper_confidence_threshold,
    ):
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.beam_size = beam_size
        self.confidence_threshold = confidence_threshold
        self.model = None
        self._load_lock = asyncio.Lock()

    def _load_model(self):
        from faster_whisper import WhisperModel

        model_path = resolve_model_path(self.model_name)
        device = self.device
        if device == "auto":
            try:
                import torch

                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

        logger.info(
            "Loading Whisper model: %s (device=%s, compute_type=%s)",
            model_path, device, self.compute_type,
        )
        self.model = WhisperModel(
            model_path,
            device=device,
            compute_type=self.compute_type,
        )
        logger.info("Whisper model loaded")

    async def ensure_loaded(self):
        if self.model is not None:
            return
        async with self._load_lock:
            if self.model is not None:
                return
            await asyncio.to_thread(self._load_model)

    async def transcribe(self, audio: np.ndarray, use_beam: bool = True) -> CTCResult | None:
        await self.ensure_loaded()
        return await asyncio.to_thread(self._transcribe_sync, audio)

    def _transcribe_sync(self, audio: np.ndarray) -> CTCResult | None:
        audio_float = audio.astype(np.float32)

        segments, info = self.model.transcribe(
            audio_float,
            language="ar",
            beam_size=self.beam_size,
            vad_filter=False,
        )

        text_parts = []
        total_log_prob = 0.0
        segment_count = 0

        for segment in segments:
            text_parts.append(segment.text.strip())
            total_log_prob += segment.avg_log_prob
            segment_count += 1

        text = " ".join(text_parts).strip()
        if not text:
            return None

        import math

        avg_log_prob = total_log_prob / max(segment_count, 1)
        confidence = min(1.0, max(0.0, math.exp(avg_log_prob)))

        logger.debug("Whisper: '%s' (confidence=%.3f)", text, confidence)

        if confidence < self.confidence_threshold:
            return None

        return CTCResult(characters=text, confidence=confidence)
