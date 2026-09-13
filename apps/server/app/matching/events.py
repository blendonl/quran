from dataclasses import dataclass, field
from enum import Enum


class LetterStatus(Enum):
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    NOT_SURE = "NOT_SURE"


@dataclass
class LetterUpdate:
    word_index: int
    letter_index: int
    status: LetterStatus


@dataclass
class LetterStatusEvent:
    surah_id: int
    ayah_number: int
    updates: list[LetterUpdate]
    confidence: float


@dataclass
class PositionEvent:
    surah_id: int
    ayah_number: int
    word_index: int
    confidence: float


@dataclass
class AyahEvent:
    event_type: str
    surah_id: int
    ayah_number: int
    text: str = ""


@dataclass
class MistakeEvent:
    surah_id: int
    ayah_number: int
    word_index: int
    expected_word: str


@dataclass
class SurahCompletedEvent:
    surah_id: int
    ayah_number: int
    next_surah_id: int | None


@dataclass
class TajweedUpdate:
    word_index: int
    letter_index: int
    rule: str
    grade: str


@dataclass
class TajweedStatusEvent:
    surah_id: int
    ayah_number: int
    updates: list[TajweedUpdate]


@dataclass
class RecitationErrorDetail:
    error_type: str
    speech_error_type: str
    expected_phoneme: str
    predicted_phoneme: str
    uthmani_start: int
    uthmani_end: int
    tajweed_rule: str | None = None
    expected_len: int | None = None
    predicted_len: int | None = None


@dataclass
class RecitationErrorEvent:
    surah_id: int
    ayah_number: int
    errors: list[RecitationErrorDetail]


@dataclass
class WordStatusUpdate:
    word_index: int
    status: str
    confidence: float
    tajweed_grade: str | None = None


@dataclass
class WordStatusEvent:
    surah_id: int
    ayah_number: int
    updates: list[WordStatusUpdate]


@dataclass
class TrackerOutput:
    positions: list[PositionEvent] = field(default_factory=list)
    ayah_events: list[AyahEvent] = field(default_factory=list)
    mistakes: list[MistakeEvent] = field(default_factory=list)
    letter_statuses: list[LetterStatusEvent] = field(default_factory=list)
    tajweed_statuses: list[TajweedStatusEvent] = field(default_factory=list)
    recitation_errors: list[RecitationErrorEvent] = field(default_factory=list)
    surah_completed: list[SurahCompletedEvent] = field(default_factory=list)
    word_statuses: list[WordStatusEvent] = field(default_factory=list)
    locating_timeout: bool = False
