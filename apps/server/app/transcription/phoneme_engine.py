import asyncio
import logging
import re

import numpy as np
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

from app.config import resolve_model_path, settings
from app.transcription.phoneme_result import PhonemeResult

logger = logging.getLogger(__name__)

TORCH_DTYPES = {
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
    "float32": torch.float32,
}

IPA_SPLIT_PATTERN = re.compile(r"([a-zðθʃʒŋɲʔʕħɣɾʁχβɸɤɹɻɬɮʐʂɕʑʋʙʀɢɴʜʢɨʉɯɵɘœɶɐɜɞɝæʊɪəɛɔʌɑɒɚːˈˌ̃ˤ]+)", re.UNICODE)


class PhonemeEngine:
    def __init__(
        self,
        model_name: str = settings.phoneme_model,
        device: str = settings.ctc_device,
        torch_dtype: str = settings.ctc_torch_dtype,
    ):
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device
        self.dtype = TORCH_DTYPES.get(torch_dtype, torch.float32)
        self.model_name = model_name
        self.processor = None
        self.model = None
        self._load_lock = asyncio.Lock()

    def _load_model(self):
        model_path = resolve_model_path(self.model_name)
        logger.info("Loading phoneme model: %s (device=%s, dtype=%s)", model_path, self.device, self.dtype)
        self.processor = Wav2Vec2Processor.from_pretrained(model_path, local_files_only=True)
        self.model = Wav2Vec2ForCTC.from_pretrained(
            model_path,
            torch_dtype=self.dtype,
            local_files_only=True,
        ).to(self.device)
        self.model.eval()
        logger.info("Phoneme model loaded")

    async def ensure_loaded(self):
        if self.model is not None:
            return
        async with self._load_lock:
            if self.model is not None:
                return
            await asyncio.to_thread(self._load_model)

    async def transcribe(self, audio: np.ndarray) -> PhonemeResult | None:
        await self.ensure_loaded()
        return await asyncio.to_thread(self._transcribe_sync, audio)

    def _transcribe_sync(self, audio: np.ndarray) -> PhonemeResult | None:
        if not self._has_speech(audio):
            return None

        inputs = self.processor(
            audio.astype(np.float32),
            sampling_rate=settings.audio_sample_rate,
            return_tensors="pt",
            padding=True,
        )
        input_values = inputs.input_values.to(self.device, dtype=self.dtype)

        with torch.no_grad():
            logits = self.model(input_values).logits

        return self._decode(logits)

    def _decode(self, logits: torch.Tensor) -> PhonemeResult | None:
        log_probs = torch.log_softmax(logits, dim=-1)
        predicted_ids = torch.argmax(logits, dim=-1)

        max_log_probs = log_probs.gather(2, predicted_ids.unsqueeze(-1)).squeeze(-1)
        non_blank_mask = predicted_ids != self.processor.tokenizer.pad_token_id
        if not non_blank_mask.any():
            return None

        raw_text = self.processor.batch_decode(predicted_ids)[0].strip()
        if not raw_text:
            return None

        frame_probs = max_log_probs[0]
        frame_ids = predicted_ids[0]

        phonemes: list[str] = []
        confidences: list[float] = []

        prev_id = -1
        current_phoneme_probs: list[float] = []

        for i in range(len(frame_ids)):
            token_id = frame_ids[i].item()
            if token_id == self.processor.tokenizer.pad_token_id:
                if current_phoneme_probs and prev_id != -1:
                    token_str = self.processor.tokenizer.decode([prev_id]).strip()
                    if token_str:
                        phonemes.append(token_str)
                        confidences.append(sum(current_phoneme_probs) / len(current_phoneme_probs))
                    current_phoneme_probs = []
                    prev_id = -1
                continue

            if token_id != prev_id:
                if current_phoneme_probs and prev_id != -1:
                    token_str = self.processor.tokenizer.decode([prev_id]).strip()
                    if token_str:
                        phonemes.append(token_str)
                        confidences.append(sum(current_phoneme_probs) / len(current_phoneme_probs))
                current_phoneme_probs = [frame_probs[i].exp().item()]
                prev_id = token_id
            else:
                current_phoneme_probs.append(frame_probs[i].exp().item())

        if current_phoneme_probs and prev_id != -1:
            token_str = self.processor.tokenizer.decode([prev_id]).strip()
            if token_str:
                phonemes.append(token_str)
                confidences.append(sum(current_phoneme_probs) / len(current_phoneme_probs))

        if not phonemes:
            return None

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        if avg_conf < settings.phoneme_confidence_threshold:
            return None

        raw_ipa = "".join(phonemes)
        logger.info("Phoneme: '%s' (avg_conf=%.3f, n=%d)", raw_ipa, avg_conf, len(phonemes))
        return PhonemeResult(phonemes=phonemes, confidences=confidences, raw_ipa=raw_ipa)

    @staticmethod
    def _has_speech(audio: np.ndarray) -> bool:
        rms = np.sqrt(np.mean(audio**2))
        return rms > settings.audio_energy_threshold
