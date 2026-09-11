import asyncio
import logging
import math
import re

import numpy as np
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

from app.config import resolve_model_path, settings
from app.transcription.ctc_result import CTCResult

logger = logging.getLogger(__name__)

TORCH_DTYPES = {
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
    "float32": torch.float32,
}


class CTCEngine:
    def __init__(
        self,
        model_name: str = settings.ctc_model,
        device: str = settings.ctc_device,
        torch_dtype: str = settings.ctc_torch_dtype,
        decode_mode: str = settings.ctc_decode_mode,
    ):
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device
        self.dtype = TORCH_DTYPES.get(torch_dtype, torch.float32)
        self.model_name = model_name
        self.decode_mode = decode_mode
        self.processor = None
        self.model = None
        self.beam_decoder = None
        self._load_lock = asyncio.Lock()

    def _load_model(self):
        model_path = resolve_model_path(self.model_name)
        logger.info("Loading CTC model: %s (device=%s, dtype=%s)", model_path, self.device, self.dtype)
        self.processor = Wav2Vec2Processor.from_pretrained(model_path, local_files_only=True)
        self.model = Wav2Vec2ForCTC.from_pretrained(
            model_path,
            torch_dtype=self.dtype,
            local_files_only=True,
        ).to(self.device)
        self.model.eval()
        logger.info("CTC model loaded")

    async def ensure_loaded(self):
        if self.model is not None:
            return
        async with self._load_lock:
            if self.model is not None:
                return
            await asyncio.to_thread(self._load_model)

    def build_beam_decoder(self, unigrams: list[str]):
        from pyctcdecode import build_ctcdecoder

        from app.transcription.lexicon import build_labels

        labels = build_labels(self.processor)
        self.beam_decoder = build_ctcdecoder(labels, unigrams=unigrams)
        logger.info("Beam decoder built with %d unigrams", len(unigrams))

    async def get_logits(self, audio: np.ndarray) -> torch.Tensor:
        await self.ensure_loaded()
        return await asyncio.to_thread(self._get_logits_sync, audio)

    def _get_logits_sync(self, audio: np.ndarray) -> torch.Tensor:
        inputs = self.processor(
            audio.astype(np.float32),
            sampling_rate=settings.audio_sample_rate,
            return_tensors="pt",
            padding=True,
        )
        input_values = inputs.input_values.to(self.device, dtype=self.dtype)
        with torch.no_grad():
            return self.model(input_values).logits

    def get_vocab(self) -> dict[str, int]:
        return self.processor.tokenizer.get_vocab()

    async def transcribe(self, audio: np.ndarray, use_beam: bool = True) -> CTCResult | None:
        await self.ensure_loaded()
        return await asyncio.to_thread(self._transcribe_sync, audio, use_beam)

    def _transcribe_sync(self, audio: np.ndarray, use_beam: bool = True) -> CTCResult | None:
        inputs = self.processor(
            audio.astype(np.float32),
            sampling_rate=settings.audio_sample_rate,
            return_tensors="pt",
            padding=True,
        )
        input_values = inputs.input_values.to(self.device, dtype=self.dtype)

        with torch.no_grad():
            logits = self.model(input_values).logits

        if use_beam and self.decode_mode == "beam" and self.beam_decoder is not None:
            return self._decode_beam(logits)
        return self._decode_greedy(logits)

    def _decode_greedy(self, logits: torch.Tensor) -> CTCResult | None:
        log_probs = torch.log_softmax(logits, dim=-1)
        predicted_ids = torch.argmax(logits, dim=-1)

        max_log_probs = log_probs.gather(2, predicted_ids.unsqueeze(-1)).squeeze(-1)
        non_blank_mask = predicted_ids != self.processor.tokenizer.pad_token_id
        if non_blank_mask.any():
            confidence = max_log_probs[non_blank_mask].mean().exp().item()
        else:
            return None

        characters = self.processor.batch_decode(predicted_ids)[0].strip()

        if not characters:
            return None

        if confidence < settings.ctc_confidence_threshold:
            return None

        logger.debug("CTC greedy: '%s' (confidence=%.3f)", characters, confidence)
        return CTCResult(characters=characters, confidence=confidence)

    def _decode_beam(self, logits: torch.Tensor) -> CTCResult | None:
        log_probs = torch.log_softmax(logits, dim=-1).cpu().numpy().astype(np.float32)[0]

        beams = self.beam_decoder.decode_beams(
            log_probs,
            beam_width=settings.ctc_beam_width,
            beam_prune_logp=settings.ctc_beam_prune_logp,
            token_min_logp=settings.ctc_beam_token_min_logp,
        )

        if not beams:
            return self._decode_greedy(logits)

        from app.transcription.lexicon import PLACEHOLDER_PATTERN

        text, _, _, logit_score, _ = beams[0]
        text = PLACEHOLDER_PATTERN.sub("", text)
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            return self._decode_greedy(logits)

        confidence = math.exp(logit_score / max(len(text), 1))

        if confidence < settings.ctc_confidence_threshold:
            return None

        logger.debug("CTC beam: '%s' (confidence=%.3f)", text, confidence)
        return CTCResult(characters=text, confidence=confidence)
