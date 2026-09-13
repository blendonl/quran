import asyncio
import logging

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class NoiseFilter:
    def __init__(
        self,
        enabled: bool = settings.noise_reduction_enabled,
        agc_enabled: bool = settings.noise_reduction_agc,
        agc_target_rms: float = settings.noise_reduction_agc_target_rms,
        agc_max_gain: float = settings.noise_reduction_agc_max_gain,
    ):
        self.enabled = enabled
        self.agc_enabled = agc_enabled
        self.agc_target_rms = agc_target_rms
        self.agc_max_gain = agc_max_gain
        self._df_model = None
        self._df_state = None
        self._available = True
        self._load_lock = asyncio.Lock()

    async def ensure_loaded(self):
        if not self.enabled or self._df_model is not None or not self._available:
            return
        async with self._load_lock:
            if self._df_model is not None or not self._available:
                return
            await asyncio.to_thread(self._load_model)

    def _load_model(self):
        try:
            from df.enhance import init_df

            self._df_model, self._df_state, _ = init_df()
            logger.info("DeepFilterNet3 loaded")
        except ImportError:
            logger.warning("deepfilternet not installed — noise reduction disabled")
            self._available = False
        except Exception as e:
            logger.warning("Failed to load DeepFilterNet3: %s", e)
            self._available = False

    async def filter(self, audio: np.ndarray) -> np.ndarray:
        if not self.enabled:
            return audio

        if self.agc_enabled:
            audio = self._apply_agc(audio)

        if not self._available or self._df_model is None:
            return audio

        return await asyncio.to_thread(self._filter_sync, audio)

    def _apply_agc(self, audio: np.ndarray) -> np.ndarray:
        rms = np.sqrt(np.mean(audio**2))
        if rms < 1e-6:
            return audio

        gain = min(self.agc_target_rms / rms, self.agc_max_gain)
        if abs(gain - 1.0) < 0.05:
            return audio

        return np.clip(audio * gain, -1.0, 1.0).astype(audio.dtype)

    def _filter_sync(self, audio: np.ndarray) -> np.ndarray:
        from df.enhance import enhance
        from scipy.signal import resample_poly

        upsampled = resample_poly(audio, 3, 1).astype(np.float32)

        import torch

        audio_tensor = torch.from_numpy(upsampled).unsqueeze(0)
        enhanced = enhance(self._df_model, self._df_state, audio_tensor)
        enhanced_np = enhanced.squeeze(0).numpy()

        downsampled = resample_poly(enhanced_np, 1, 3).astype(np.float32)

        return downsampled
