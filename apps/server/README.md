# Quran Recitation Server

Real-time Quran recitation tracking server built with FastAPI and faster-whisper.

## Requirements

- Python >= 3.11

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,beam]"
```

## Fetch Quran Data

```bash
yarn fetch-data
# or
python scripts/fetch_quran_data.py
```

## Run

```bash
yarn dev
# or
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server runs at http://localhost:8000.

## Phoneme Engines

The server supports three phoneme engines, selectable via `QURAN_PHONEME_ENGINE_TYPE`:

| Engine | Model | Description |
|---|---|---|
| `espeak` (default) | `facebook/wav2vec2-xlsr-53-espeak-cv-ft` | English-pretrained IPA model |
| `nrshoudi` | `nrshoudi/wav2vec2-large-xls-r-300m-Arabic-phonemeIPA` | Arabic-pretrained IPA model, drop-in replacement |
| `muaalem` | `obadx/muaalem-model-v3_2` | Quran-specific model with tajweed sifat features |

### espeak / nrshoudi

No extra dependencies. These use the same Wav2Vec2ForCTC pipeline with different model weights.

```bash
# default
uvicorn app.main:app --reload

# nrshoudi
QURAN_PHONEME_ENGINE_TYPE=nrshoudi uvicorn app.main:app --reload
```

### muaalem

Requires extra dependencies. Note: `quran-muaalem` requires `numpy>=2.2.6` which conflicts with `pyctcdecode`'s `numpy<2.0` pin, so the `beam` and `muaalem` extras cannot be installed together. CTC greedy decoding is used instead when beam is not installed.

```bash
pip install -e ".[muaalem]"
QURAN_PHONEME_ENGINE_TYPE=muaalem uvicorn app.main:app --reload
```

The muaalem engine produces tajweed sifat features (hams/jahr, shidda/rakhawa, tafkheem/tarqeeq, qalqala, ghunna) in addition to letter statuses.

## Configuration

All settings are configurable via environment variables with the `QURAN_` prefix:

| Variable | Default | Description |
|---|---|---|
| `QURAN_PHONEME_ENGINE_TYPE` | `espeak` | Phoneme engine (`espeak`, `nrshoudi`, `muaalem`) |
| `QURAN_CTC_MODEL` | `jonatasgrosman/wav2vec2-large-xlsr-53-arabic` | CTC text model |
| `QURAN_CTC_DEVICE` | `auto` | Device (`cpu`, `cuda`, `auto`) |
| `QURAN_AUDIO_SAMPLE_RATE` | `16000` | Audio sample rate in Hz |
| `QURAN_VAD_AGGRESSIVENESS` | `2` | VAD aggressiveness (0-3) |
| `QURAN_QURAN_DATA_PATH` | `app/quran/data/quran_uthmani.json` | Path to Quran data |

## Tests

```bash
yarn test
# or
python -m pytest tests/ -v
```

## Lint

```bash
yarn lint
# or
ruff check app/ tests/
```
