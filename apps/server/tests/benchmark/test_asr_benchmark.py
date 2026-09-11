import logging
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import numpy as np
import pytest

from app.config import settings
from app.quran.corpus import QuranCorpus

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "audio"
BASE_URL = "https://everyayah.com/data"
RECITER = "Alafasy_128kbps"
SURAH_ID = 1
AYAH_COUNT = 7


def _download_and_convert(ayah: int, output_dir: Path) -> Path:
    filename = f"{SURAH_ID:03d}{ayah:03d}"
    pcm_path = output_dir / f"{filename}.pcm"

    if pcm_path.exists() and pcm_path.stat().st_size > 0:
        return pcm_path

    mp3_url = f"{BASE_URL}/{RECITER}/{filename}.mp3"
    mp3_path = output_dir / f"{filename}.mp3"

    logger.info("Downloading %s", mp3_url)
    urllib.request.urlretrieve(mp3_url, mp3_path)

    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(mp3_path),
            "-ar", "16000", "-ac", "1", "-f", "s16le",
            str(pcm_path),
        ],
        check=True,
        capture_output=True,
    )
    mp3_path.unlink(missing_ok=True)
    return pcm_path


def _ensure_audio() -> list[Path]:
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not found in PATH")

    output_dir = FIXTURES_DIR / RECITER
    output_dir.mkdir(parents=True, exist_ok=True)
    pcm_files = []
    for ayah in range(1, AYAH_COUNT + 1):
        try:
            pcm_files.append(_download_and_convert(ayah, output_dir))
        except Exception as e:
            pytest.skip(f"Failed to download audio {SURAH_ID}:{ayah}: {e}")
    return pcm_files


def _load_pcm(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    int16 = np.frombuffer(raw, dtype=np.int16)
    return int16.astype(np.float32) / 32768.0


def _get_reference_texts() -> list[str]:
    corpus = QuranCorpus(Path(settings.quran_data_path))
    texts = []
    for ayah_num in range(1, AYAH_COUNT + 1):
        ayah = corpus.get_ayah(SURAH_ID, ayah_num)
        texts.append(ayah.text)
    return texts


def compute_cer(reference: str, hypothesis: str) -> float:
    ref_chars = list(reference.replace(" ", ""))
    hyp_chars = list(hypothesis.replace(" ", ""))
    d = _levenshtein(ref_chars, hyp_chars)
    return d / max(len(ref_chars), 1)


def compute_wer(reference: str, hypothesis: str) -> float:
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    d = _levenshtein(ref_words, hyp_words)
    return d / max(len(ref_words), 1)


def _levenshtein(ref: list, hyp: list) -> int:
    n, m = len(ref), len(hyp)
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        curr = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[m]


@pytest.fixture(scope="module")
def audio_files():
    return _ensure_audio()


@pytest.fixture(scope="module")
def reference_texts():
    return _get_reference_texts()


@pytest.mark.benchmark
class TestNemoCtc:
    @pytest.fixture(autouse=True)
    def _skip_if_unavailable(self):
        try:
            import torch  # noqa: F401
            import nemo.collections.asr  # noqa: F401
        except ImportError:
            pytest.skip("NeMo/torch not available")

    def test_nemo_ctc(self, audio_files, reference_texts):
        import asyncio

        from app.transcription.nemo_engine import NemoCtcEngine

        engine = NemoCtcEngine()
        asyncio.get_event_loop().run_until_complete(engine.ensure_loaded())

        for i, (pcm_path, ref_text) in enumerate(zip(audio_files, reference_texts)):
            audio = _load_pcm(pcm_path)
            start = time.monotonic()
            result = asyncio.get_event_loop().run_until_complete(engine.transcribe(audio))
            latency = time.monotonic() - start

            hyp = result.characters if result else ""
            cer = compute_cer(ref_text, hyp)
            wer = compute_wer(ref_text, hyp)
            logger.info(
                "NeMo | ayah=%d | CER=%.3f | WER=%.3f | latency=%.2fs | conf=%.3f | hyp='%s'",
                i + 1, cer, wer, latency,
                result.confidence if result else 0.0, hyp,
            )


@pytest.mark.benchmark
class TestWhisperLargeV3Turbo:
    @pytest.fixture(autouse=True)
    def _skip_if_unavailable(self):
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            pytest.skip("faster-whisper not available")

    def test_whisper_large_v3_turbo(self, audio_files, reference_texts):
        import asyncio

        from app.transcription.whisper_engine import WhisperEngine

        engine = WhisperEngine(model_name=settings.whisper_model)
        asyncio.get_event_loop().run_until_complete(engine.ensure_loaded())

        for i, (pcm_path, ref_text) in enumerate(zip(audio_files, reference_texts)):
            audio = _load_pcm(pcm_path)
            start = time.monotonic()
            result = asyncio.get_event_loop().run_until_complete(engine.transcribe(audio))
            latency = time.monotonic() - start

            hyp = result.characters if result else ""
            cer = compute_cer(ref_text, hyp)
            wer = compute_wer(ref_text, hyp)
            logger.info(
                "Whisper-v3-turbo | ayah=%d | CER=%.3f | WER=%.3f | latency=%.2fs | conf=%.3f | hyp='%s'",
                i + 1, cer, wer, latency,
                result.confidence if result else 0.0, hyp,
            )


@pytest.mark.benchmark
class TestTarteelQuranWhisper:
    @pytest.fixture(autouse=True)
    def _skip_if_unavailable(self):
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            pytest.skip("faster-whisper not available")

    def test_tarteel_quran_whisper(self, audio_files, reference_texts):
        import asyncio

        from app.transcription.whisper_engine import WhisperEngine

        engine = WhisperEngine(model_name=settings.tarteel_model)
        asyncio.get_event_loop().run_until_complete(engine.ensure_loaded())

        for i, (pcm_path, ref_text) in enumerate(zip(audio_files, reference_texts)):
            audio = _load_pcm(pcm_path)
            start = time.monotonic()
            result = asyncio.get_event_loop().run_until_complete(engine.transcribe(audio))
            latency = time.monotonic() - start

            hyp = result.characters if result else ""
            cer = compute_cer(ref_text, hyp)
            wer = compute_wer(ref_text, hyp)
            logger.info(
                "Tarteel | ayah=%d | CER=%.3f | WER=%.3f | latency=%.2fs | conf=%.3f | hyp='%s'",
                i + 1, cer, wer, latency,
                result.confidence if result else 0.0, hyp,
            )


@pytest.mark.benchmark
class TestQuranPhonemeWav2vec2:
    @pytest.fixture(autouse=True)
    def _skip_if_unavailable(self):
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except ImportError:
            pytest.skip("torch/transformers not available")

    def test_quran_phoneme_wav2vec2(self, audio_files, reference_texts):
        import asyncio

        from app.transcription.quran_phoneme_engine import QuranPhonemeEngine

        engine = QuranPhonemeEngine()
        asyncio.get_event_loop().run_until_complete(engine.ensure_loaded())

        for i, (pcm_path, ref_text) in enumerate(zip(audio_files, reference_texts)):
            audio = _load_pcm(pcm_path)
            start = time.monotonic()
            result = asyncio.get_event_loop().run_until_complete(engine.transcribe(audio))
            latency = time.monotonic() - start

            hyp = result.raw_ipa if result else ""
            logger.info(
                "QuranPhoneme | ayah=%d | latency=%.2fs | conf=%.3f | phonemes='%s'",
                i + 1, latency,
                (sum(result.confidences) / len(result.confidences)) if result else 0.0,
                hyp,
            )
