from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np

from app.transcription.ctc_result import CTCResult
from app.transcription.muaalem_result import MuaalemResult
from app.transcription.phoneme_result import PhonemeResult

if TYPE_CHECKING:
    from app.transcription.forced_align import ForcedAlignResult

logger = logging.getLogger(__name__)

MAX_ENGINE_RETRIES = 3


class EngineMode(Enum):
    CTC_TEXT = "ctc_text"
    PHONEME = "phoneme"
    MUAALEM = "muaalem"
    FORCED_ALIGN = "forced_align"


class EngineOutput:
    def __init__(
        self,
        mode: EngineMode,
        ctc_result: CTCResult | None = None,
        phoneme_result: PhonemeResult | None = None,
        muaalem_result: MuaalemResult | None = None,
    ):
        self.mode = mode
        self.ctc_result = ctc_result
        self.phoneme_result = phoneme_result
        self.muaalem_result = muaalem_result


class EngineRouter:
    def __init__(
        self,
        ctc_engine,
        phoneme_engine=None,
        muaalem_engine=None,
    ):
        self.ctc_engine = ctc_engine
        self.phoneme_engine = phoneme_engine
        self.muaalem_engine = muaalem_engine
        self._phoneme_available: bool | None = None
        self._muaalem_available: bool | None = None
        self._phoneme_fail_count: int = 0
        self._muaalem_fail_count: int = 0

    async def ensure_loaded(self):
        if not self._phoneme_available:
            self._phoneme_available = None
        if not self._muaalem_available:
            self._muaalem_available = None
        self._phoneme_fail_count = 0
        self._muaalem_fail_count = 0
        await self.ctc_engine.ensure_loaded()

    async def _ensure_phoneme_loaded(self) -> bool:
        if self._phoneme_available is True:
            return True
        if self.phoneme_engine is None:
            return False
        if self._phoneme_fail_count >= MAX_ENGINE_RETRIES:
            return False
        try:
            await self.phoneme_engine.ensure_loaded()
            self._phoneme_available = True
            self._phoneme_fail_count = 0
            return True
        except Exception as e:
            self._phoneme_fail_count += 1
            logger.warning(
                "Phoneme engine unavailable (attempt %d/%d), falling back to CTC: %s",
                self._phoneme_fail_count, MAX_ENGINE_RETRIES, e,
            )
            return False

    async def ensure_muaalem_loaded(self) -> bool:
        if self._muaalem_available is True:
            return True
        if self.muaalem_engine is None:
            return False
        if self._muaalem_fail_count >= MAX_ENGINE_RETRIES:
            return False
        try:
            await self.muaalem_engine.ensure_loaded()
            self._muaalem_available = True
            self._muaalem_fail_count = 0
            return True
        except Exception as e:
            self._muaalem_fail_count += 1
            logger.warning(
                "Muaalem engine unavailable (attempt %d/%d), falling back to CTC: %s",
                self._muaalem_fail_count, MAX_ENGINE_RETRIES, e,
            )
            return False

    async def forced_align(
        self,
        audio: np.ndarray,
        expected_text: str,
        expected_words: list[str],
    ) -> ForcedAlignResult | None:
        if not hasattr(self.ctc_engine, "get_logits"):
            logger.debug("Forced alignment unavailable: engine has no get_logits")
            return None

        import torch

        from app.transcription.forced_align import (
            ForcedAlignResult as FA,
            build_word_token_ranges,
            extract_word_boundaries,
            run_forced_align,
            text_to_tokens,
        )

        try:
            logits = await self.ctc_engine.get_logits(audio)
            log_probs = torch.log_softmax(logits, dim=-1).squeeze(0).cpu()
            num_frames = log_probs.size(0)

            vocab = self.ctc_engine.get_vocab()
            blank_id = vocab.get("[PAD]", vocab.get("<pad>", 0))

            words_to_align = self._fit_words_to_frames(
                expected_words, vocab, num_frames, text_to_tokens,
            )
            if not words_to_align:
                return None

            all_text = "".join(words_to_align)
            tokens = text_to_tokens(all_text, vocab)
            if not tokens:
                return None

            word_ranges = build_word_token_ranges(words_to_align, vocab)

            aligned_tokens, scores = run_forced_align(log_probs, tokens, blank_id)

            boundaries = extract_word_boundaries(
                aligned_tokens, scores, word_ranges, blank_id,
            )

            return FA(
                word_boundaries=boundaries,
                total_frames=num_frames,
            )
        except Exception as e:
            logger.warning("Forced alignment failed: %s", e)
            return None

    @staticmethod
    def _fit_words_to_frames(
        words: list[str], vocab: dict[str, int], num_frames: int, text_to_tokens_fn=None,
    ) -> list[str]:
        if text_to_tokens_fn is None:
            from app.transcription.forced_align import text_to_tokens as text_to_tokens_fn

        tokens = text_to_tokens_fn("".join(words), vocab)
        num_repeats = sum(
            1 for i in range(1, len(tokens)) if tokens[i] == tokens[i - 1]
        )
        if len(tokens) + num_repeats <= num_frames:
            return words

        fitted: list[str] = []
        token_count = 0
        prev_token = -1
        for word in words:
            word_tokens = text_to_tokens_fn(word, vocab)
            repeats = 0
            for t in word_tokens:
                if t == prev_token:
                    repeats += 1
                prev_token = t
            new_count = token_count + len(word_tokens) + repeats
            if new_count > num_frames:
                break
            fitted.append(word)
            token_count = new_count

        return fitted

    async def transcribe(
        self,
        audio: np.ndarray,
        mode: EngineMode,
        surah_id: int | None = None,
        ayah_number: int | None = None,
        use_beam: bool = True,
    ) -> EngineOutput | None:
        if mode == EngineMode.CTC_TEXT:
            result = await self.ctc_engine.transcribe(audio, use_beam=use_beam)
            if result is None:
                return None
            return EngineOutput(mode=EngineMode.CTC_TEXT, ctc_result=result)

        if mode == EngineMode.MUAALEM:
            if surah_id is not None and ayah_number is not None:
                if await self.ensure_muaalem_loaded():
                    result = await self.muaalem_engine.transcribe(audio, surah_id, ayah_number)
                    if result is None:
                        return None
                    return EngineOutput(mode=EngineMode.MUAALEM, muaalem_result=result)
            result = await self.ctc_engine.transcribe(audio, use_beam=use_beam)
            if result is None:
                return None
            return EngineOutput(mode=EngineMode.CTC_TEXT, ctc_result=result)

        if await self._ensure_phoneme_loaded():
            result = await self.phoneme_engine.transcribe(audio)
            if result is None:
                return None
            return EngineOutput(mode=EngineMode.PHONEME, phoneme_result=result)

        result = await self.ctc_engine.transcribe(audio, use_beam=use_beam)
        if result is None:
            return None
        return EngineOutput(mode=EngineMode.CTC_TEXT, ctc_result=result)
