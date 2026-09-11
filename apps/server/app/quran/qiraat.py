from dataclasses import dataclass, field
from enum import Enum


class QiraahName(Enum):
    HAFS = "hafs"
    WARSH = "warsh"


@dataclass(frozen=True)
class QiraahConfig:
    name: QiraahName
    ipa_data_file: str
    idghaam_letters: frozenset[str] = frozenset("يرملون")
    ikhfaa_letters: frozenset[str] = frozenset("تثجدذزسشصضطظفقك")
    iqlab_letter: str = "ب"
    izhar_letters: frozenset[str] = frozenset("ءهعحغخ")
    qalqalah_letters: frozenset[str] = frozenset("قطبجد")
    ghunnah_letters: frozenset[str] = frozenset("نم")
    madd_natural_length: int = 2
    madd_connected_length: int = 4
    madd_separated_length: int = 4


HAFS_CONFIG = QiraahConfig(
    name=QiraahName.HAFS,
    ipa_data_file="ipa_hafs.json",
)

QIRAAT_REGISTRY: dict[QiraahName, QiraahConfig] = {
    QiraahName.HAFS: HAFS_CONFIG,
}


def get_qiraah(name: str = "hafs") -> QiraahConfig:
    qiraah_name = QiraahName(name)
    return QIRAAT_REGISTRY[qiraah_name]
