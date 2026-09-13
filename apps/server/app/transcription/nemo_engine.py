import asyncio
import logging

import numpy as np
import torch

from app.config import resolve_model_path, settings
from app.transcription.ctc_result import CTCResult

logger = logging.getLogger(__name__)


class NemoCtcEngine:
    def __init__(
        self,
        model_name: str = settings.ctc_model,
        device: str = settings.ctc_device,
    ):
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device
        self.model_name = model_name
        self.model = None
        self._load_lock = asyncio.Lock()

    def _load_model(self):
        import nemo.collections.asr as nemo_asr

        model_path = resolve_model_path(self.model_name)
        logger.info("Loading NeMo CTC model: %s (device=%s)", model_path, self.device)

        self.model = nemo_asr.models.EncDecHybridRNNTCTCBPEModel.from_pretrained(
            model_name=model_path,
        )
        self.model = self.model.to(self.device)
        self.model.eval()
        self.model.encoder.set_default_att_context_size([70, 13])

        self.model.change_decoding_strategy(decoder_type="ctc")

        logger.info("NeMo CTC model loaded")

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
        logger.debug("NeMo transcribing: %d samples (%.2fs)", len(audio_float), len(audio_float) / 16000)

        with torch.no_grad():
            output = self.model.transcribe(
                [audio_float], batch_size=1, return_hypotheses=True,
            )

        if not output:
            return None

        hyp = output[0]
        if hasattr(hyp, "text"):
            text = hyp.text.strip()
            score = getattr(hyp, "score", None)
        else:
            text = str(hyp).strip()
            score = None

        if not text:
            return None

        confidence = 0.7
        if score is not None:
            import math
            length = max(len(text), 1)
            confidence = min(1.0, max(0.0, math.exp(score / length)))

        logger.debug("NeMo CTC: '%s' (confidence=%.3f, score=%s)", text, confidence, score)

        if confidence < settings.ctc_confidence_threshold:
            return None

        return CTCResult(characters=text, confidence=confidence)

    async def get_logits(self, audio: np.ndarray) -> torch.Tensor:
        await self.ensure_loaded()
        return await asyncio.to_thread(self._get_logits_sync, audio)

    def _get_logits_sync(self, audio: np.ndarray) -> torch.Tensor:
        audio_float = audio.astype(np.float32)
        audio_tensor = torch.tensor(audio_float).unsqueeze(0).to(self.device)
        audio_length = torch.tensor([len(audio_float)], dtype=torch.long).to(self.device)

        with torch.no_grad():
            processed, processed_len = self.model.preprocessor(
                input_signal=audio_tensor,
                length=audio_length,
            )
            encoded, encoded_len = self.model.encoder(
                audio_signal=processed,
                length=processed_len,
            )
            log_probs = self.model.ctc_decoder(encoder_output=encoded)

        return log_probs

    def get_vocab(self) -> dict[str, int]:
        tokenizer = self.model.tokenizer
        vocab = {}
        for i in range(tokenizer.vocab_size):
            token = tokenizer.ids_to_tokens([i])
            if token:
                vocab[token[0]] = i
        return vocab

