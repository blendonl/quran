import json
import logging
from pathlib import Path

from app.quran.ipa_converter import IPAUnit

logger = logging.getLogger(__name__)


class IPADatabase:
    def __init__(self):
        self._data: dict[tuple[int, int], list[IPAUnit]] = {}

    def load(self, path: Path):
        with open(path) as f:
            data = json.load(f)

        for entry in data["ayahs"]:
            key = (entry["surah_id"], entry["ayah_number"])
            units = [
                IPAUnit(
                    ipa=u["ipa"],
                    arabic_word_index=u["arabic_word_index"],
                    arabic_letter_index=u["arabic_letter_index"],
                    tajweed_rule=u.get("tajweed_rule"),
                    is_geminated=u.get("is_geminated", False),
                    madd_type=u.get("madd_type"),
                )
                for u in entry["ipa_units"]
            ]
            self._data[key] = units

        logger.info("Loaded IPA data for %d ayahs", len(self._data))

    def get_ipa(self, surah_id: int, ayah_number: int) -> list[IPAUnit] | None:
        return self._data.get((surah_id, ayah_number))

    @property
    def loaded(self) -> bool:
        return len(self._data) > 0
