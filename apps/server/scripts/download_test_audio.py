#!/usr/bin/env python3
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://everyayah.com/data"
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "audio"

RECITERS = [
    "Alafasy_128kbps",
    "Abdul_Basit_Murattal_64kbps",
    "Husary_128kbps",
]

SURAH_ID = 1
AYAH_COUNT = 7


def download_and_convert(reciter: str, surah: int, ayah: int, output_dir: Path) -> Path:
    filename = f"{surah:03d}{ayah:03d}"
    pcm_path = output_dir / f"{filename}.pcm"

    if pcm_path.exists() and pcm_path.stat().st_size > 0:
        return pcm_path

    mp3_url = f"{BASE_URL}/{reciter}/{filename}.mp3"
    mp3_path = output_dir / f"{filename}.mp3"

    print(f"  Downloading {mp3_url}")
    urllib.request.urlretrieve(mp3_url, mp3_path)

    print(f"  Converting to PCM: {pcm_path.name}")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(mp3_path),
            "-ar", "16000", "-ac", "1", "-f", "s16le",
            str(pcm_path),
        ],
        check=True,
        capture_output=True,
    )

    mp3_path.unlink(missing_ok=True)
    return pcm_path


def main():
    if not shutil.which("ffmpeg"):
        print("ERROR: ffmpeg not found in PATH", file=sys.stderr)
        sys.exit(1)

    for reciter in RECITERS:
        output_dir = FIXTURES_DIR / reciter
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n=== {reciter} ===")

        for ayah in range(1, AYAH_COUNT + 1):
            pcm_path = download_and_convert(reciter, SURAH_ID, ayah, output_dir)
            size_kb = pcm_path.stat().st_size / 1024
            print(f"  {pcm_path.name}: {size_kb:.0f} KB")

    print("\nDone.")


if __name__ == "__main__":
    main()
