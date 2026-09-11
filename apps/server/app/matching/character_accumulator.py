from app.quran.normalizer import normalize
from app.transcription.ctc_result import CTCResult


class CharacterAccumulator:
    def __init__(self):
        self._raw_chars = ""
        self._normalized = ""
        self._normalized_no_spaces = ""

    @property
    def normalized(self) -> str:
        return self._normalized

    @property
    def normalized_no_spaces(self) -> str:
        return self._normalized_no_spaces

    @property
    def length(self) -> int:
        return len(self._normalized_no_spaces)

    def add_chunk(self, ctc_result: CTCResult) -> str:
        self._raw_chars += ctc_result.characters
        self._normalized = normalize(self._raw_chars)
        self._normalized_no_spaces = self._normalized.replace(" ", "")
        return self._normalized_no_spaces

    def reset(self):
        self._raw_chars = ""
        self._normalized = ""
        self._normalized_no_spaces = ""
