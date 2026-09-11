import bisect
import json
from dataclasses import dataclass, field
from pathlib import Path

from app.quran.normalizer import normalize, split_words, TASHKEEL_PATTERN


@dataclass
class QuranWord:
    surah_id: int
    ayah_number: int
    word_index: int
    text: str
    normalized: str


@dataclass
class QuranAyah:
    surah_id: int
    ayah_number: int
    text: str
    words: list[str]
    normalized_words: list[str]
    normalized_text: str
    normalized_text_no_spaces: str
    uthmani_char_map: list[tuple[int, int]] = field(default_factory=list)
    word_to_letters: dict[int, list[tuple[int, int]]] = field(default_factory=dict)
    pos_to_wl: dict[int, tuple[int, int]] = field(default_factory=dict)
    char_to_word_offsets: list[int] = field(default_factory=list)


@dataclass
class QuranSurah:
    id: int
    name_simple: str
    name_arabic: str
    verses_count: int
    ayahs: list[QuranAyah]


def _build_uthmani_char_map(uthmani_words: list[str], normalized_words: list[str]) -> list[tuple[int, int]]:
    char_map: list[tuple[int, int]] = []
    for word_idx, word in enumerate(uthmani_words):
        letter_idx = 0
        for ch in word:
            if TASHKEEL_PATTERN.match(ch):
                continue
            char_map.append((word_idx, letter_idx))
            letter_idx += 1
    return char_map


def _build_word_to_letters(char_map: list[tuple[int, int]]) -> dict[int, list[tuple[int, int]]]:
    result: dict[int, list[tuple[int, int]]] = {}
    for wi, li in char_map:
        result.setdefault(wi, []).append((wi, li))
    return result


def _build_pos_to_wl(uthmani_words: list[str]) -> dict[int, tuple[int, int]]:
    pos_to_wl: dict[int, tuple[int, int]] = {}
    pos = 0
    for word_idx, word in enumerate(uthmani_words):
        letter_idx = 0
        for ch in word:
            if not TASHKEEL_PATTERN.match(ch):
                pos_to_wl[pos] = (word_idx, letter_idx)
                letter_idx += 1
            pos += 1
        pos += 1
    return pos_to_wl


def _build_char_to_word_offsets(normalized_words: list[str]) -> list[int]:
    offsets: list[int] = []
    cumulative = 0
    for word in normalized_words:
        cumulative += len(word)
        offsets.append(cumulative)
    return offsets


class QuranCorpus:
    def __init__(self, data_path: Path):
        self.surahs: dict[int, QuranSurah] = {}
        self.ayahs: dict[tuple[int, int], QuranAyah] = {}

        self._load(data_path)

    def _load(self, data_path: Path):
        with open(data_path) as f:
            data = json.load(f)

        for surah_data in data["surahs"]:
            surah_id = surah_data["id"]
            ayah_list = []

            for ayah_data in surah_data["ayahs"]:
                ayah_number = ayah_data["ayah_number"]
                text = ayah_data["text_uthmani"]
                words = text.split()
                normalized_words = split_words(text)
                normalized_text = normalize(text)
                normalized_text_no_spaces = normalized_text.replace(" ", "")

                uthmani_char_map = _build_uthmani_char_map(words, normalized_words)
                word_to_letters = _build_word_to_letters(uthmani_char_map)
                pos_to_wl = _build_pos_to_wl(words)
                char_to_word_offsets = _build_char_to_word_offsets(normalized_words)

                ayah = QuranAyah(
                    surah_id=surah_id,
                    ayah_number=ayah_number,
                    text=text,
                    words=words,
                    normalized_words=normalized_words,
                    normalized_text=normalized_text,
                    normalized_text_no_spaces=normalized_text_no_spaces,
                    uthmani_char_map=uthmani_char_map,
                    word_to_letters=word_to_letters,
                    pos_to_wl=pos_to_wl,
                    char_to_word_offsets=char_to_word_offsets,
                )
                ayah_list.append(ayah)
                self.ayahs[(surah_id, ayah_number)] = ayah

            self.surahs[surah_id] = QuranSurah(
                id=surah_id,
                name_simple=surah_data["name_simple"],
                name_arabic=surah_data["name_arabic"],
                verses_count=surah_data["verses_count"],
                ayahs=ayah_list,
            )

    def get_ayah(self, surah_id: int, ayah_number: int) -> QuranAyah | None:
        return self.ayahs.get((surah_id, ayah_number))

    def get_next_ayah(self, surah_id: int, ayah_number: int) -> QuranAyah | None:
        next_ayah = self.ayahs.get((surah_id, ayah_number + 1))
        if next_ayah:
            return next_ayah
        next_surah = self.surahs.get(surah_id + 1)
        if next_surah and next_surah.ayahs:
            return next_surah.ayahs[0]
        return None
