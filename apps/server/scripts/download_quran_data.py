import json
import sys
from pathlib import Path
from urllib.request import urlopen, Request

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "app" / "quran" / "data" / "quran_uthmani.json"
API_BASE = "https://api.quran.com/api/v4"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "QuranRecitationApp/1.0",
}


def api_get(url: str):
    req = Request(url, headers=HEADERS)
    with urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_surahs():
    data = api_get(f"{API_BASE}/chapters")
    return data["chapters"]


def fetch_ayahs(surah_id: int):
    ayahs = []
    page = 1
    while True:
        data = api_get(f"{API_BASE}/quran/verses/uthmani?chapter_number={surah_id}&page={page}")
        for verse in data["verses"]:
            key_parts = verse["verse_key"].split(":")
            ayahs.append({
                "ayah_number": int(key_parts[1]),
                "text_uthmani": verse["text_uthmani"],
            })
        pagination = data.get("pagination", {})
        if page >= pagination.get("total_pages", 1):
            break
        page += 1
    return ayahs


def main():
    print("Fetching surah list...")
    chapters = fetch_surahs()

    surahs = []
    for ch in chapters:
        surah_id = ch["id"]
        print(f"  Surah {surah_id}: {ch['name_simple']}")
        ayahs = fetch_ayahs(surah_id)
        surahs.append({
            "id": surah_id,
            "name_simple": ch["name_simple"],
            "name_arabic": ch["name_arabic"],
            "verses_count": ch["verses_count"],
            "ayahs": ayahs,
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"surahs": surahs}, f, ensure_ascii=False, indent=2)

    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
