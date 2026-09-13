import json
import tempfile
from pathlib import Path

import pytest

from app.quran.corpus import QuranCorpus
from app.matching.prefix_index import PrefixIndex
from app.matching.phonetic import to_phonetic
from app.quran.normalizer import normalize


@pytest.fixture
def corpus():
    data = {
        "surahs": [
            {
                "id": 1,
                "name_simple": "Al-Fatihah",
                "name_arabic": "الفاتحة",
                "verses_count": 3,
                "ayahs": [
                    {
                        "ayah_number": 1,
                        "verse_key": "1:1",
                        "text_uthmani": "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
                    },
                    {
                        "ayah_number": 2,
                        "verse_key": "1:2",
                        "text_uthmani": "ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ",
                    },
                    {
                        "ayah_number": 3,
                        "verse_key": "1:3",
                        "text_uthmani": "ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
                    },
                ],
            }
        ]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f, ensure_ascii=False)
        f.flush()
        return QuranCorpus(Path(f.name))


@pytest.fixture
def index(corpus):
    return PrefixIndex(corpus)


def _phonetic_normalize(text: str) -> str:
    return to_phonetic(normalize(text).replace(" ", ""))


def test_search_bismillah(index):
    query = _phonetic_normalize("بسم الله")
    results = index.search(query)
    assert len(results) > 0
    assert any(r.surah_id == 1 and r.ayah_number == 1 for r in results)


def test_search_alhamd(index):
    query = _phonetic_normalize("الحمد لله")
    results = index.search(query)
    assert len(results) > 0
    assert any(r.surah_id == 1 and r.ayah_number == 2 for r in results)


def test_search_no_match(index):
    query = to_phonetic("ظظظظظ")
    results = index.search(query)
    assert len(results) == 0


def test_narrow_candidates(index):
    prefix_short = _phonetic_normalize("الرحم")
    candidates = index.search(prefix_short)
    assert len(candidates) > 1

    prefix_long = _phonetic_normalize("الرحمن الرحيم")
    narrowed = index.narrow(candidates, prefix_long)
    assert len(narrowed) <= len(candidates)
    assert len(narrowed) > 0


def test_word_index_mapping(index):
    query = _phonetic_normalize("بسم")
    results = index.search(query)
    bismillah_results = [r for r in results if r.surah_id == 1 and r.ayah_number == 1]
    assert len(bismillah_results) > 0
    assert bismillah_results[0].word_index == 0


def test_search_returns_start_char(index):
    query = _phonetic_normalize("بسم")
    results = index.search(query)
    bismillah = [r for r in results if r.surah_id == 1 and r.ayah_number == 1]
    assert len(bismillah) > 0
    assert bismillah[0].start_char == 0


def test_phonetic_matching(index):
    query_with_sad = _phonetic_normalize("بصم")
    query_with_sin = _phonetic_normalize("بسم")
    results_sad = index.search(query_with_sad)
    results_sin = index.search(query_with_sin)
    assert len(results_sad) == len(results_sin)
    assert all(
        a.surah_id == b.surah_id and a.ayah_number == b.ayah_number
        for a, b in zip(results_sad, results_sin)
    )


def test_word_boundary_only(index):
    query = _phonetic_normalize("سم")
    results = index.search(query)
    assert len(results) == 0


def test_narrowing_reduces_candidates(index):
    short_query = _phonetic_normalize("الرحم")
    candidates = index.search(short_query)
    assert len(candidates) >= 2

    long_query = _phonetic_normalize("الرحمنالرحيم")
    narrowed = index.narrow(candidates, long_query)
    assert len(narrowed) <= len(candidates)

    too_long = to_phonetic("الرحمنالرحيمزززززز")
    empty = index.narrow(narrowed, too_long)
    assert len(empty) == 0
