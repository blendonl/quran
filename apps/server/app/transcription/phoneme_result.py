from dataclasses import dataclass


@dataclass
class PhonemeResult:
    phonemes: list[str]
    confidences: list[float]
    raw_ipa: str
