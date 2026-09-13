from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    models_dir: str = ""

    ctc_engine_type: str = "nemo"
    ctc_model: str = "nvidia/stt_ar_fastconformer_hybrid_large_pc_v1.0"
    ctc_device: str = "auto"
    ctc_torch_dtype: str = "float32"
    ctc_confidence_threshold: float = 0.3
    ctc_decode_mode: str = "beam"
    ctc_beam_width: int = 10
    ctc_beam_prune_logp: float = -10.0
    ctc_beam_token_min_logp: float = -5.0

    phoneme_model: str = "facebook/wav2vec2-xlsr-53-espeak-cv-ft"
    phoneme_confidence_threshold: float = 0.25

    whisper_model: str = "openai/whisper-large-v3-turbo"
    whisper_device: str = "auto"
    whisper_compute_type: str = "float16"
    whisper_beam_size: int = 5
    whisper_confidence_threshold: float = 0.3

    tarteel_model: str = "tarteel-ai/whisper-base-ar-quran"

    quran_phoneme_model: str = "TBOGamer22/wav2vec2-quran-phonetics"

    phoneme_engine_type: str = "espeak"
    nrshoudi_model: str = "nrshoudi/wav2vec2-large-xls-r-300m-Arabic-phonemeIPA"
    muaalem_model: str = "obadx/muaalem-model-v3_2"
    muaalem_torch_dtype: str = "bfloat16"

    noise_reduction_enabled: bool = True
    noise_reduction_agc: bool = True
    noise_reduction_agc_target_rms: float = 0.1
    noise_reduction_agc_max_gain: float = 20.0

    qiraah: str = "hafs"

    audio_max_buffer_s: float = 30.0
    audio_emit_interval_s: float = 0.25
    audio_min_locate_s: float = 0.5
    audio_max_locate_snapshot_s: float = 5.0
    audio_max_tracking_snapshot_s: float = 3.0
    audio_sample_rate: int = 16000

    vad_threshold: float = 0.5
    vad_aggressiveness: int = 2
    min_speech_frames: int = 3

    audio_energy_threshold: float = 0.008
    silence_reset_chunks: int = 6

    quran_data_path: str = "app/quran/data/quran_uthmani.json"
    ipa_data_path: str = "app/quran/data/ipa_hafs.json"

    max_locate_attempts: int = 40

    matching_track_threshold: float = 0.55
    matching_muaalem_correct_threshold: float = 0.55
    matching_ayah_complete_ratio: float = 0.95
    forced_align_min_audio_s: float = 0.5
    forced_align_word_threshold: float = 0.5

    matching_mistake_threshold: float = 0.4
    matching_consecutive_failures: int = 3
    matching_transition_grace_cycles: int = 3

    matching_phoneme_correct_threshold: float = 0.2
    matching_phoneme_not_sure_threshold: float = 0.6
    matching_phoneme_match_threshold: float = 0.4
    matching_phoneme_per_phoneme_ceiling: float = 0.7

    matching_tajweed_excellent: float = 0.15
    matching_tajweed_good: float = 0.35
    matching_tajweed_needs_work: float = 0.6

    letter_confidence_gate: float = 0.45

    model_config = {"env_prefix": "QURAN_", "env_file": ".env"}


settings = Settings()


def resolve_model_path(model_name: str) -> str:
    if settings.models_dir:
        local_path = Path(settings.models_dir) / model_name
        if local_path.is_dir():
            return str(local_path)
    return model_name
