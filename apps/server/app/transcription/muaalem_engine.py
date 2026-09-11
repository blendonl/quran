import asyncio
import logging
import os
from collections import OrderedDict, defaultdict
from dataclasses import dataclass

import numpy as np
import torch

from app.config import resolve_model_path, settings
from app.transcription.muaalem_result import MuaalemResult, SifaResult

logger = logging.getLogger(__name__)

try:
    from quran_transcript import Aya, quran_phonetizer
    from quran_transcript.phonetics.sifa import chunck_phonemes
    from quran_transcript.phonetics.error_explainer import (
        align_phonemes_groups,
        extract_ref_phonetic_to_uthmani,
    )
    _HAS_QURAN_TRANSCRIPT = True
except ImportError:
    _HAS_QURAN_TRANSCRIPT = False


@dataclass
class _RefData:
    uthmani_ref: str
    phonetizer_out: object
    ref_phonemes: str
    ref_groups: list
    ref_ph_to_uthmani: dict
    uthmani_char_to_word: dict[int, int]
    ref_group_to_word: list[int]

TORCH_DTYPES = {
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
    "float32": torch.float32,
}

SIFA_ATTRS = [
    "hams_or_jahr",
    "shidda_or_rakhawa",
    "tafkheem_or_taqeeq",
    "qalqla",
    "ghonna",
    "itbaq",
    "safeer",
    "tikraar",
    "tafashie",
    "istitala",
]


class MuaalemEngine:
    def __init__(
        self,
        model_name: str = settings.muaalem_model,
        device: str = settings.ctc_device,
        torch_dtype: str = settings.ctc_torch_dtype,
        rewaya: str = settings.qiraah,
    ):
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device
        self.dtype = TORCH_DTYPES.get(torch_dtype, torch.float32)
        self.model_name = model_name
        self.rewaya = rewaya
        self._muaalem = None
        self._moshaf = None
        self._load_lock = asyncio.Lock()
        self._ref_cache: OrderedDict[tuple[int, int], _RefData] = OrderedDict()
        self._ref_cache_max = 50

    def _load_model(self):
        from quran_muaalem import Muaalem
        from quran_transcript import MoshafAttributes

        self._patch_align_predicted_sequence()

        model_path = resolve_model_path(self.model_name)
        logger.info("Loading Muaalem model: %s (device=%s, dtype=%s)", model_path, self.device, self.dtype)

        prev = os.environ.get("HF_HUB_OFFLINE")
        os.environ["HF_HUB_OFFLINE"] = "1"
        try:
            self._muaalem = Muaalem(model_name_or_path=model_path, device=self.device, dtype=self.dtype)
        finally:
            if prev is None:
                os.environ.pop("HF_HUB_OFFLINE", None)
            else:
                os.environ["HF_HUB_OFFLINE"] = prev
        self._moshaf = MoshafAttributes(
            rewaya=self.rewaya,
            madd_monfasel_len=2,
            madd_mottasel_len=4,
            madd_mottasel_waqf=4,
            madd_aared_len=2,
        )
        logger.info("Muaalem model loaded")

    @staticmethod
    def _patch_align_predicted_sequence():
        from quran_muaalem import decode as decode_module

        original = decode_module.align_predicted_sequence

        def patched(ref, predicted, missing_placeholder=-100):
            if len(predicted) == 0:
                return [missing_placeholder] * len(ref), [False] * len(ref)
            return original(ref, predicted, missing_placeholder)

        decode_module.align_predicted_sequence = patched

    async def ensure_loaded(self):
        if self._muaalem is not None:
            return
        async with self._load_lock:
            if self._muaalem is not None:
                return
            await asyncio.to_thread(self._load_model)

    async def transcribe(
        self, audio: np.ndarray, surah_id: int, ayah_number: int
    ) -> MuaalemResult | None:
        await self.ensure_loaded()
        return await asyncio.to_thread(self._transcribe_sync, audio, surah_id, ayah_number)

    def _get_ref_data(self, surah_id: int, ayah_number: int) -> _RefData | None:
        key = (surah_id, ayah_number)
        if key in self._ref_cache:
            self._ref_cache.move_to_end(key)
            return self._ref_cache[key]

        if not _HAS_QURAN_TRANSCRIPT:
            return None

        aya_data = Aya(surah_id, ayah_number).get()
        uthmani_ref = aya_data.uthmani
        phonetizer_out = quran_phonetizer(uthmani_ref, self._moshaf, remove_spaces=True)
        ref_phonemes = phonetizer_out.phonemes if hasattr(phonetizer_out, "phonemes") else ""

        ref_groups = chunck_phonemes(ref_phonemes) if ref_phonemes else []

        try:
            ref_ph_to_uthmani = extract_ref_phonetic_to_uthmani(phonetizer_out.mappings)
        except (ValueError, IndexError):
            ref_ph_to_uthmani = {}

        words = uthmani_ref.split()
        uthmani_char_to_word: dict[int, int] = {}
        pos = 0
        for word_idx, word in enumerate(words):
            for i in range(len(word)):
                uthmani_char_to_word[pos + i] = word_idx
            pos += len(word) + 1

        ref_group_to_word: list[int] = []
        ph_pos = 0
        for group in ref_groups:
            uthmani_idx = ref_ph_to_uthmani.get(ph_pos)
            if uthmani_idx is not None:
                word_idx = uthmani_char_to_word.get(uthmani_idx, 0)
            else:
                word_idx = ref_group_to_word[-1] if ref_group_to_word else 0
            ref_group_to_word.append(word_idx)
            ph_pos += len(group)

        ref_data = _RefData(
            uthmani_ref=uthmani_ref,
            phonetizer_out=phonetizer_out,
            ref_phonemes=ref_phonemes,
            ref_groups=ref_groups,
            ref_ph_to_uthmani=ref_ph_to_uthmani,
            uthmani_char_to_word=uthmani_char_to_word,
            ref_group_to_word=ref_group_to_word,
        )
        self._ref_cache[key] = ref_data
        if len(self._ref_cache) > self._ref_cache_max:
            self._ref_cache.popitem(last=False)
        return ref_data

    def _transcribe_sync(
        self, audio: np.ndarray, surah_id: int, ayah_number: int
    ) -> MuaalemResult | None:
        ref_data = self._get_ref_data(surah_id, ayah_number)
        if ref_data is None:
            return None

        try:
            outs = self._muaalem(
                [audio.astype(np.float32)],
                [ref_data.phonetizer_out],
                sampling_rate=settings.audio_sample_rate,
            )
        except (ValueError, RuntimeError, IndexError) as e:
            logger.warning("Muaalem decode error for %d:%d: %s", surah_id, ayah_number, e)
            return None
        out = outs[0]

        probs = out.phonemes.probs
        if isinstance(probs, torch.Tensor):
            probs = probs.tolist()

        avg_conf = sum(probs) / len(probs) if probs else 0.0
        if avg_conf < settings.phoneme_confidence_threshold:
            return None

        sifat = []
        for sifa in out.sifat:
            result = SifaResult(phoneme_group=sifa.phonemes_group)
            for attr in SIFA_ATTRS:
                val = getattr(sifa, attr, None)
                if val is not None:
                    setattr(result, attr, val.text)
                    setattr(result, f"{attr}_conf", val.prob)
            sifat.append(result)

        phoneme_groups = [s.phonemes_group for s in out.sifat]

        word_phoneme_map = self._build_word_phoneme_map(ref_data, out.sifat)

        logger.debug(
            "Muaalem: '%s' (avg_conf=%.3f, groups=%d)",
            out.phonemes.text, avg_conf, len(phoneme_groups),
        )

        return MuaalemResult(
            phonemes_text=out.phonemes.text,
            phoneme_groups=phoneme_groups,
            confidences=probs,
            sifat=sifat,
            ref_phonemes_len=len(ref_data.ref_phonemes),
            word_phoneme_map=word_phoneme_map,
            uthmani_text=ref_data.uthmani_ref,
            ref_phonemes=ref_data.ref_phonemes,
            phonetizer_mappings=ref_data.phonetizer_out.mappings,
        )

    @staticmethod
    def _build_word_phoneme_map(ref_data: _RefData, pred_sifat) -> list[dict] | None:
        if not _HAS_QURAN_TRANSCRIPT:
            return None

        ref_groups = ref_data.ref_groups
        pred_groups = [s.phonemes_group for s in pred_sifat]

        if not ref_groups or not pred_groups:
            return None

        try:
            alignments = align_phonemes_groups(ref_groups, pred_groups)
        except Exception:
            logger.debug("MUAALEM _build_word_phoneme_map: alignment failed")
            return None

        logger.debug(
            "MUAALEM alignment: ref_groups=%d pred_groups=%d ops=%s",
            len(ref_groups), len(pred_groups),
            [(a.op_type, a.ref_idx, a.pred_idx) for a in alignments[:20]],
        )

        ref_group_to_word = ref_data.ref_group_to_word
        pred_to_word = {}
        for align in alignments:
            if align.op_type in ("equal", "replace") and align.pred_idx < len(pred_groups):
                if align.ref_idx < len(ref_group_to_word):
                    pred_to_word[align.pred_idx] = ref_group_to_word[align.ref_idx]

        if not pred_to_word:
            logger.debug("MUAALEM _build_word_phoneme_map: no pred_to_word mappings")
            return None

        word_sifat_indices = defaultdict(list)
        for pred_idx, word_idx in pred_to_word.items():
            word_sifat_indices[word_idx].append(pred_idx)

        words = ref_data.uthmani_ref.split()
        result = []
        for word_idx in sorted(word_sifat_indices.keys()):
            indices = sorted(word_sifat_indices[word_idx])
            result.append({
                "word_index": word_idx,
                "word": words[word_idx] if word_idx < len(words) else "",
                "phonemes": "".join(pred_groups[i] for i in indices),
                "sifat_start": indices[0],
                "sifat_end": indices[-1] + 1,
            })

        if result:
            logger.debug(
                "MUAALEM word_map: %s",
                [(r["word_index"], r["word"], r["sifat_start"], r["sifat_end"]) for r in result],
            )
        return result if result else None
