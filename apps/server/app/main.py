import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger("app").setLevel(logging.INFO)
logging.getLogger("uvicorn").setLevel(logging.INFO)

from app.config import settings
from app.quran.corpus import QuranCorpus
from app.quran.ipa_database import IPADatabase
from app.matching.prefix_index import PrefixIndex
from app.transcription.engine_router import EngineRouter
from app.transcription.muaalem_engine import MuaalemEngine
from app.api.router import router as api_router
from app.ws.router import router as ws_router

logger = logging.getLogger(__name__)


def _create_ctc_engine():
    if settings.ctc_engine_type == "whisper":
        from app.transcription.whisper_engine import WhisperEngine

        return WhisperEngine(model_name=settings.whisper_model)

    if settings.ctc_engine_type == "tarteel":
        from app.transcription.whisper_engine import WhisperEngine

        return WhisperEngine(model_name=settings.tarteel_model)

    if settings.ctc_engine_type == "nemo":
        from app.transcription.nemo_engine import NemoCtcEngine

        return NemoCtcEngine(
            model_name=settings.ctc_model,
            device=settings.ctc_device,
        )

    from app.transcription.ctc_engine import CTCEngine

    return CTCEngine(
        model_name=settings.ctc_model,
        device=settings.ctc_device,
        torch_dtype=settings.ctc_torch_dtype,
        decode_mode=settings.ctc_decode_mode,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    data_path = Path(settings.quran_data_path)
    if data_path.exists():
        app.state.corpus = QuranCorpus(data_path)
    else:
        app.state.corpus = None

    ctc_engine = _create_ctc_engine()

    use_beam = (
        settings.ctc_engine_type == "wav2vec2"
        and settings.ctc_decode_mode == "beam"
        and app.state.corpus is not None
    )

    if use_beam:
        from app.transcription.lexicon import build_unigrams

        model_task = asyncio.create_task(ctc_engine.ensure_loaded())
        unigrams = await asyncio.to_thread(build_unigrams, app.state.corpus)
        await model_task
        await asyncio.to_thread(ctc_engine.build_beam_decoder, unigrams)
    else:
        await ctc_engine.ensure_loaded()

    app.state.ctc_engine = ctc_engine

    if settings.phoneme_engine_type == "muaalem":
        muaalem_engine = MuaalemEngine(
            model_name=settings.muaalem_model,
            device=settings.ctc_device,
            torch_dtype=settings.muaalem_torch_dtype,
        )
        await muaalem_engine.ensure_loaded()
        app.state.phoneme_engine = None
        app.state.engine_router = EngineRouter(ctc_engine, muaalem_engine=muaalem_engine)
    else:
        from app.transcription.phoneme_engine import PhonemeEngine

        model_name = (
            settings.nrshoudi_model
            if settings.phoneme_engine_type == "nrshoudi"
            else settings.phoneme_model
        )
        phoneme_engine = PhonemeEngine(
            model_name=model_name,
            device=settings.ctc_device,
            torch_dtype=settings.ctc_torch_dtype,
        )
        await phoneme_engine.ensure_loaded()
        app.state.phoneme_engine = phoneme_engine
        app.state.engine_router = EngineRouter(ctc_engine, phoneme_engine)

    ipa_db = IPADatabase()
    ipa_path = Path(settings.ipa_data_path)
    if ipa_path.exists():
        await asyncio.to_thread(ipa_db.load, ipa_path)
    else:
        logger.warning("IPA data not found at %s", ipa_path)
    app.state.ipa_database = ipa_db

    if app.state.corpus:
        app.state.prefix_index = PrefixIndex(app.state.corpus)
    else:
        app.state.prefix_index = None

    if settings.noise_reduction_enabled:
        from app.audio.noise_filter import NoiseFilter

        noise_filter = NoiseFilter()
        await noise_filter.ensure_loaded()
        app.state.noise_filter = noise_filter
    else:
        app.state.noise_filter = None

    yield

    app.state.ctc_engine = None
    app.state.phoneme_engine = None
    app.state.engine_router = None
    app.state.ipa_database = None
    app.state.corpus = None
    app.state.prefix_index = None
    app.state.noise_filter = None


app = FastAPI(title="Quran Recitation Server", lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)
