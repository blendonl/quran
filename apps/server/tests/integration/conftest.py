import logging
import shutil
import subprocess
import urllib.request
from pathlib import Path

import numpy as np
import pytest

from app.config import settings
from app.quran.corpus import QuranCorpus
from app.quran.ipa_database import IPADatabase
from app.matching.prefix_index import PrefixIndex

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "audio"
BASE_URL = "https://everyayah.com/data"

SURAH_ID = 1
AYAH_COUNT = 7


def _download_and_convert(reciter: str, surah: int, ayah: int, output_dir: Path) -> Path:
    filename = f"{surah:03d}{ayah:03d}"
    pcm_path = output_dir / f"{filename}.pcm"

    if pcm_path.exists() and pcm_path.stat().st_size > 0:
        logger.info("Cached: %s/%s", reciter, pcm_path.name)
        return pcm_path

    mp3_url = f"{BASE_URL}/{reciter}/{filename}.mp3"
    mp3_path = output_dir / f"{filename}.mp3"

    logger.info("Downloading %s", mp3_url)
    urllib.request.urlretrieve(mp3_url, mp3_path)

    logger.info("Converting %s to PCM", filename)
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


def _ensure_reciter_audio(reciter: str) -> list[Path]:
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not found in PATH")

    logger.info("Preparing audio for %s", reciter)
    output_dir = FIXTURES_DIR / reciter
    output_dir.mkdir(parents=True, exist_ok=True)
    pcm_files = []

    for ayah in range(1, AYAH_COUNT + 1):
        try:
            pcm_path = _download_and_convert(reciter, SURAH_ID, ayah, output_dir)
            pcm_files.append(pcm_path)
        except Exception as e:
            pytest.skip(f"Failed to download audio for {reciter} {SURAH_ID}:{ayah}: {e}")

    return pcm_files


@pytest.fixture(scope="session")
def audio_fixtures() -> dict[str, list[Path]]:
    return {}


@pytest.fixture
def reciter_audio(request, audio_fixtures) -> list[Path]:
    reciter = request.param if hasattr(request, "param") else request.node.callspec.params.get("reciter")
    if reciter not in audio_fixtures:
        audio_fixtures[reciter] = _ensure_reciter_audio(reciter)
    return audio_fixtures[reciter]


@pytest.fixture(scope="session")
def corpus() -> QuranCorpus:
    return QuranCorpus(Path(settings.quran_data_path))


@pytest.fixture(scope="session")
def prefix_index(corpus: QuranCorpus) -> PrefixIndex:
    return PrefixIndex(corpus)


@pytest.fixture(scope="session")
def ipa_database() -> IPADatabase | None:
    path = Path(settings.ipa_data_path)
    if not path.exists():
        return None
    db = IPADatabase()
    db.load(path)
    return db


@pytest.fixture(scope="session")
def engine_router():
    try:
        import torch
    except ImportError:
        pytest.skip("torch not available")

    from app.transcription.engine_router import EngineRouter

    if settings.ctc_engine_type == "nemo":
        from app.transcription.nemo_engine import NemoCtcEngine
        ctc_engine = NemoCtcEngine()
    else:
        from app.transcription.ctc_engine import CTCEngine
        ctc_engine = CTCEngine()

    muaalem_engine = None
    try:
        from app.transcription.muaalem_engine import MuaalemEngine
        muaalem_engine = MuaalemEngine()
    except Exception:
        pass

    yield EngineRouter(ctc_engine=ctc_engine, muaalem_engine=muaalem_engine)

    import gc

    if hasattr(ctc_engine, 'model'):
        del ctc_engine.model
        ctc_engine.model = None
    if hasattr(ctc_engine, 'processor'):
        del ctc_engine.processor
        ctc_engine.processor = None

    if muaalem_engine is not None:
        muaalem_engine._muaalem = None
        muaalem_engine._moshaf = None

    gc.collect()
    torch.cuda.empty_cache()


def load_pcm_as_int16(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    return np.frombuffer(raw, dtype=np.int16)
