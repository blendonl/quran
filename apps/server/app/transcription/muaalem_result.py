from dataclasses import dataclass
from typing import Any


@dataclass
class SifaResult:
    phoneme_group: str
    hams_or_jahr: str | None = None
    hams_or_jahr_conf: float = 0.0
    shidda_or_rakhawa: str | None = None
    shidda_or_rakhawa_conf: float = 0.0
    tafkheem_or_taqeeq: str | None = None
    tafkheem_or_taqeeq_conf: float = 0.0
    qalqla: str | None = None
    qalqla_conf: float = 0.0
    ghonna: str | None = None
    ghonna_conf: float = 0.0
    itbaq: str | None = None
    itbaq_conf: float = 0.0
    safeer: str | None = None
    safeer_conf: float = 0.0
    tikraar: str | None = None
    tikraar_conf: float = 0.0
    tafashie: str | None = None
    tafashie_conf: float = 0.0
    istitala: str | None = None
    istitala_conf: float = 0.0


@dataclass
class MuaalemResult:
    phonemes_text: str
    phoneme_groups: list[str]
    confidences: list[float]
    sifat: list[SifaResult]
    ref_phonemes_len: int = 0
    word_phoneme_map: list[dict] | None = None
    uthmani_text: str = ""
    ref_phonemes: str = ""
    phonetizer_mappings: Any = None
