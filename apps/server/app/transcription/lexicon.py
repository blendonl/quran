import re

from app.quran.corpus import QuranCorpus

TASHKEEL_PATTERN = re.compile(r"[\u064B-\u0652\u0670\u0640]")
PLACEHOLDER_PATTERN = re.compile(r"\u2800\d+")


def build_labels(processor) -> list[str]:
    vocab = processor.tokenizer.get_vocab()
    labels = [token for token, _ in sorted(vocab.items(), key=lambda x: x[1])]
    seen: set[str] = set()
    result: list[str] = []
    placeholder_idx = 0
    for label in labels:
        cleaned = TASHKEEL_PATTERN.sub("", label)
        if cleaned in seen:
            cleaned = f"\u2800{placeholder_idx}"
            placeholder_idx += 1
        seen.add(cleaned)
        result.append(cleaned)
    return result


def build_unigrams(corpus: QuranCorpus) -> list[str]:
    words: set[str] = set()
    for ayah in corpus.ayahs.values():
        words.update(ayah.normalized_words)
    return sorted(words)
