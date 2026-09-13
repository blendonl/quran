import logging

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
MAX_FRAME_SIZE = 960


class OpusDecoder:
    def __init__(self, sample_rate: int = SAMPLE_RATE, channels: int = CHANNELS):
        import opuslib

        self._decoder = opuslib.Decoder(sample_rate, channels)
        self._frame_size = MAX_FRAME_SIZE

    def decode(self, opus_data: bytes) -> bytes:
        return self._decoder.decode(opus_data, self._frame_size)
