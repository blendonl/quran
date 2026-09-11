#!/usr/bin/env python3
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.quran.corpus import QuranCorpus
from app.quran.ipa_converter import convert_ayah_to_ipa, ayah_ipa_to_string
from app.quran.qiraat import get_qiraah


def generate(
    quran_data_path: str = "app/quran/data/quran_uthmani.json",
    qiraah_name: str = "hafs",
    output_path: str | None = None,
):
    corpus = QuranCorpus(Path(quran_data_path))
    qiraah = get_qiraah(qiraah_name)

    if output_path is None:
        output_path = f"app/quran/data/ipa_{qiraah_name}.json"

    ayahs = []
    for (surah_id, ayah_number), ayah in sorted(corpus.ayahs.items()):
        units = convert_ayah_to_ipa(ayah.words, qiraah)
        ayahs.append({
            "surah_id": surah_id,
            "ayah_number": ayah_number,
            "ipa_string": ayah_ipa_to_string(units),
            "ipa_units": [asdict(u) for u in units],
        })

    result = {
        "qiraah": qiraah_name,
        "ayah_count": len(ayahs),
        "ayahs": ayahs,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=None)

    print(f"Generated IPA data: {len(ayahs)} ayahs → {output_path}")


if __name__ == "__main__":
    qiraah = sys.argv[1] if len(sys.argv) > 1 else "hafs"
    generate(qiraah_name=qiraah)
