from dataclasses import dataclass


@dataclass
class CTCResult:
    characters: str
    confidence: float
