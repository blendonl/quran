from unittest.mock import MagicMock

from app.transcription.lexicon import build_labels, build_unigrams


class TestBuildLabels:
    def test_sorted_by_token_id(self):
        processor = MagicMock()
        processor.tokenizer.get_vocab.return_value = {"ب": 2, "<pad>": 0, "ا": 1}

        labels = build_labels(processor)

        assert labels == ["<pad>", "ا", "ب"]

    def test_all_tokens_included(self):
        vocab = {"a": 0, "b": 1, "c": 2, "d": 3}
        processor = MagicMock()
        processor.tokenizer.get_vocab.return_value = vocab

        labels = build_labels(processor)

        assert len(labels) == len(vocab)
        assert set(labels) == set(vocab.keys())

    def test_strips_tashkeel_with_unique_placeholders(self):
        processor = MagicMock()
        processor.tokenizer.get_vocab.return_value = {
            "<pad>": 0,
            "ب": 1,
            "\u064E": 2,  # fathah
            "\u0650": 3,  # kasrah
            "\u0651": 4,  # shadda
        }

        labels = build_labels(processor)

        assert labels[0] == "<pad>"
        assert labels[1] == "ب"
        assert len(labels) == len(set(labels))


class TestBuildUnigrams:
    def _make_corpus(self, ayahs_data):
        corpus = MagicMock()
        ayahs = {}
        for i, words in enumerate(ayahs_data):
            ayah = MagicMock()
            ayah.normalized_words = words
            ayahs[(1, i + 1)] = ayah
        corpus.ayahs = ayahs
        return corpus

    def test_unique_words(self):
        corpus = self._make_corpus([
            ["بسم", "الله", "الرحمن"],
            ["الله", "الرحمن", "الرحيم"],
        ])

        unigrams = build_unigrams(corpus)

        assert len(unigrams) == len(set(unigrams))

    def test_sorted(self):
        corpus = self._make_corpus([["ب", "ا", "ج"]])

        unigrams = build_unigrams(corpus)

        assert unigrams == sorted(unigrams)

    def test_collects_from_all_ayahs(self):
        corpus = self._make_corpus([
            ["كلمه"],
            ["اخري"],
        ])

        unigrams = build_unigrams(corpus)

        assert "كلمه" in unigrams
        assert "اخري" in unigrams

    def test_empty_corpus(self):
        corpus = self._make_corpus([])

        unigrams = build_unigrams(corpus)

        assert unigrams == []
