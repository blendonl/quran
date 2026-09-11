from pydantic import BaseModel


class SessionStart(BaseModel):
    type: str = "session.start"
    sample_rate: int = 16000
    encoding: str = "pcm_s16le"
    surah_id: int | None = None
    ayah_number: int | None = None


class SessionStop(BaseModel):
    type: str = "session.stop"


class SessionReady(BaseModel):
    type: str = "session.ready"


class PositionMessage(BaseModel):
    type: str = "position"
    surah_id: int
    ayah_number: int
    word_index: int
    confidence: float


class AyahStarted(BaseModel):
    type: str = "ayah.started"
    surah_id: int
    ayah_number: int
    text: str


class AyahCompleted(BaseModel):
    type: str = "ayah.completed"
    surah_id: int
    ayah_number: int


class TranscriptionMessage(BaseModel):
    type: str = "transcription"
    text: str
    is_partial: bool = False


class WordMistake(BaseModel):
    type: str = "word.mistake"
    surah_id: int
    ayah_number: int
    word_index: int
    expected_word: str


class LetterStatusUpdate(BaseModel):
    word_index: int
    letter_index: int
    status: str


class LetterStatusMessage(BaseModel):
    type: str = "letter.status"
    surah_id: int
    ayah_number: int
    updates: list[LetterStatusUpdate]
    confidence: float


class TajweedStatusUpdate(BaseModel):
    word_index: int
    letter_index: int
    rule: str
    grade: str


class TajweedStatusMessage(BaseModel):
    type: str = "tajweed.status"
    surah_id: int
    ayah_number: int
    updates: list[TajweedStatusUpdate]


class SurahCompleted(BaseModel):
    type: str = "surah.completed"
    surah_id: int
    ayah_number: int
    next_surah_id: int | None = None


class RecitationErrorDetail(BaseModel):
    error_type: str
    speech_error_type: str
    expected_phoneme: str
    predicted_phoneme: str
    uthmani_start: int
    uthmani_end: int
    tajweed_rule: str | None = None
    expected_len: int | None = None
    predicted_len: int | None = None


class RecitationErrorMessage(BaseModel):
    type: str = "recitation.error"
    surah_id: int
    ayah_number: int
    errors: list[RecitationErrorDetail]


class WordStatusUpdateMsg(BaseModel):
    word_index: int
    status: str
    confidence: float
    tajweed_grade: str | None = None


class WordStatusMessage(BaseModel):
    type: str = "word.status"
    surah_id: int
    ayah_number: int
    updates: list[WordStatusUpdateMsg]


class BatchMessage(BaseModel):
    type: str = "batch"
    messages: list[dict]


class LocatingTimeout(BaseModel):
    type: str = "locating.timeout"


class ErrorMessage(BaseModel):
    type: str = "error"
    message: str
