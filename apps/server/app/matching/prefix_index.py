import logging
from dataclasses import dataclass, field

from app.matching.phonetic import to_phonetic
from app.quran.corpus import QuranAyah, QuranCorpus
from app.quran.normalizer import normalize

logger = logging.getLogger(__name__)

ALEF = "\u0627"
HAMZA = "\u0621"
SKIPPABLE = {ALEF, HAMZA}

MAX_TRIE_DEPTH = 60
MAX_TRIE_RESULTS = 500


@dataclass
class MatchCandidate:
    surah_id: int
    ayah_number: int
    start_char: int
    word_index: int
    matched_end: int = 0
    match_count: int = 0


@dataclass
class TrieNode:
    children: dict[str, "TrieNode"] = field(default_factory=dict)
    candidates: list[tuple[int, int, int, int]] = field(default_factory=list)


class PrefixIndex:
    def __init__(self, corpus: QuranCorpus):
        self._ayah_lookup: dict[tuple[int, int], QuranAyah] = corpus.ayahs
        self._ayah_list: list[QuranAyah] = []
        self._char_to_word_cache: dict[tuple[int, int], list[int]] = {}
        self._phonetic_texts: dict[tuple[int, int], str] = {}
        self._word_starts: dict[tuple[int, int], set[int]] = {}
        self._trie_root = TrieNode()

        self._build(corpus)

    def _build(self, corpus: QuranCorpus):
        for surah_id in sorted(corpus.surahs.keys()):
            surah = corpus.surahs[surah_id]
            for ayah in surah.ayahs:
                self._ayah_list.append(ayah)
                key = (ayah.surah_id, ayah.ayah_number)

                words = normalize(ayah.text).split()
                self._char_to_word_cache[key] = self._map_chars_to_words(words)
                phonetic_text = to_phonetic(ayah.normalized_text_no_spaces)
                self._phonetic_texts[key] = phonetic_text

                offset = 0
                starts = set()
                for word in words:
                    starts.add(offset)
                    offset += len(word)
                self._word_starts[key] = starts

                for pos in sorted(starts):
                    word_idx = self._word_index_from_mapping(
                        self._char_to_word_cache[key], pos
                    )
                    candidate = (ayah.surah_id, ayah.ayah_number, pos, word_idx)
                    self._insert_into_trie(phonetic_text, pos, candidate)

        logger.info("PrefixIndex built: %d ayahs indexed (trie)", len(self._ayah_list))

    def _insert_into_trie(
        self, phonetic_text: str, start: int, candidate: tuple[int, int, int, int]
    ):
        node = self._trie_root
        for i in range(start, len(phonetic_text)):
            ch = phonetic_text[i]
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
            node.candidates.append(candidate)

    @staticmethod
    def _map_chars_to_words(words: list[str]) -> list[int]:
        mapping: list[int] = []
        for word_idx, word in enumerate(words):
            for _ in word:
                mapping.append(word_idx)
        return mapping

    @staticmethod
    def _word_index_from_mapping(mapping: list[int], char_offset: int) -> int:
        if not mapping:
            return 0
        if char_offset < len(mapping):
            return mapping[char_offset]
        return mapping[-1] if mapping else 0

    @staticmethod
    def _prefix_matches(text: str, start: int, query: str) -> tuple[bool, int, int]:
        ti = start
        qi = 0
        matched = 0
        while qi < len(query) and ti < len(text):
            if text[ti] == query[qi]:
                ti += 1
                qi += 1
                matched += 1
            elif matched > 0 and text[ti] in SKIPPABLE:
                ti += 1
            elif matched > 0 and query[qi] in SKIPPABLE:
                qi += 1
            else:
                return False, start, 0
        while qi < len(query):
            if query[qi] not in SKIPPABLE:
                return False, start, 0
            qi += 1
        return True, ti, matched

    def _trie_walk(self, query: str) -> list[tuple[int, int, int, int, int]]:
        results: list[tuple[int, int, int, int, int]] = []
        self._trie_walk_recursive(self._trie_root, query, 0, 0, results)
        return results

    def _trie_walk_recursive(
        self,
        node: TrieNode,
        query: str,
        qi: int,
        depth: int,
        results: list[tuple[int, int, int, int, int]],
    ):
        if depth > MAX_TRIE_DEPTH or len(results) >= MAX_TRIE_RESULTS:
            return

        if qi >= len(query):
            for candidate in node.candidates:
                results.append((*candidate, depth))
                if len(results) >= MAX_TRIE_RESULTS:
                    return
            return

        ch = query[qi]

        if ch in node.children:
            self._trie_walk_recursive(node.children[ch], query, qi + 1, depth + 1, results)

        if depth > 0 and ch in SKIPPABLE:
            self._trie_walk_recursive(node, query, qi + 1, depth, results)

        if depth > 0:
            for skip_ch in SKIPPABLE:
                if skip_ch in node.children and skip_ch != ch:
                    self._trie_walk_recursive(
                        node.children[skip_ch], query, qi, depth + 1, results
                    )

    def search(self, phonetic_prefix: str) -> list[MatchCandidate]:
        if not phonetic_prefix:
            return []

        trie_results = self._trie_walk(phonetic_prefix)

        seen: set[tuple[int, int, int]] = set()
        candidates = []
        for surah_id, ayah_number, start_char, word_idx, depth in trie_results:
            dedup_key = (surah_id, ayah_number, start_char)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            key = (surah_id, ayah_number)
            phonetic_text = self._phonetic_texts[key]
            ok, text_end, match_count = self._prefix_matches(
                phonetic_text, start_char, phonetic_prefix
            )
            if ok:
                candidates.append(
                    MatchCandidate(
                        surah_id=surah_id,
                        ayah_number=ayah_number,
                        start_char=start_char,
                        word_index=word_idx,
                        matched_end=text_end,
                        match_count=match_count,
                    )
                )

        return candidates

    def narrow(self, candidates: list[MatchCandidate], phonetic_prefix: str) -> list[MatchCandidate]:
        if not phonetic_prefix:
            return candidates

        result = []
        for c in candidates:
            key = (c.surah_id, c.ayah_number)
            phonetic_text = self._phonetic_texts.get(key)
            if not phonetic_text:
                continue
            ok, text_end, match_count = self._prefix_matches(
                phonetic_text, c.start_char, phonetic_prefix
            )
            if ok:
                result.append(
                    MatchCandidate(
                        surah_id=c.surah_id,
                        ayah_number=c.ayah_number,
                        start_char=c.start_char,
                        word_index=c.word_index,
                        matched_end=text_end,
                        match_count=match_count,
                    )
                )

        return result

    def get_word_index_at(self, surah_id: int, ayah_number: int, char_offset: int) -> int:
        mapping = self._char_to_word_cache.get((surah_id, ayah_number))
        if not mapping:
            return 0
        if char_offset < len(mapping):
            return mapping[char_offset]
        return len(mapping) - 1 if mapping else 0
