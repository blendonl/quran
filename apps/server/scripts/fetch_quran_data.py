#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import httpx

BASE_URL = "https://api.quran.com/api/v4"
OUTPUT_PATH = Path(__file__).parent.parent / "app" / "quran" / "data" / "quran_uthmani.json"


def fetch_chapters(client: httpx.Client) -> list[dict]:
    resp = client.get(f"{BASE_URL}/chapters", params={"language": "en"})
    resp.raise_for_status()
    return resp.json()["chapters"]


def fetch_verses(client: httpx.Client, chapter_id: int) -> list[dict]:
    all_verses = []
    page = 1
    while True:
        resp = client.get(
            f"{BASE_URL}/verses/by_chapter/{chapter_id}",
            params={
                "language": "en",
                "words": "false",
                "fields": "text_uthmani",
                "per_page": "50",
                "page": str(page),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        all_verses.extend(data["verses"])
        pagination = data.get("pagination", {})
        if pagination.get("next_page") is None:
            break
        page = pagination["next_page"]
    return all_verses


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    result = {"surahs": []}

    with httpx.Client(timeout=30) as client:
        chapters = fetch_chapters(client)
        print(f"Fetched {len(chapters)} chapters")

        for chapter in chapters:
            chapter_id = chapter["id"]
            print(f"  Fetching surah {chapter_id}: {chapter['name_simple']}...")

            verses = fetch_verses(client, chapter_id)

            surah_data = {
                "id": chapter_id,
                "name_simple": chapter["name_simple"],
                "name_arabic": chapter["name_arabic"],
                "verses_count": chapter["verses_count"],
                "ayahs": [
                    {
                        "ayah_number": v["verse_number"],
                        "verse_key": v["verse_key"],
                        "text_uthmani": v["text_uthmani"],
                    }
                    for v in verses
                ],
            }
            result["surahs"].append(surah_data)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Saved to {OUTPUT_PATH}")
    total_ayahs = sum(len(s["ayahs"]) for s in result["surahs"])
    print(f"Total: {len(result['surahs'])} surahs, {total_ayahs} ayahs")


if __name__ == "__main__":
    main()
