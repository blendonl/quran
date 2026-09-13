from app.matching.character_accumulator import CharacterAccumulator
from app.transcription.ctc_result import CTCResult


def test_accumulates_characters():
    acc = CharacterAccumulator()
    acc.add_chunk(CTCResult(characters="بسم", confidence=0.9))
    acc.add_chunk(CTCResult(characters=" الله", confidence=0.9))
    assert "بسم" in acc.normalized_no_spaces
    assert "الله" in acc.normalized_no_spaces


def test_strips_diacritics():
    acc = CharacterAccumulator()
    acc.add_chunk(CTCResult(characters="بِسْمِ", confidence=0.9))
    assert acc.normalized_no_spaces == "بسم"


def test_normalizes_hamza():
    acc = CharacterAccumulator()
    acc.add_chunk(CTCResult(characters="أحمد", confidence=0.9))
    assert acc.normalized_no_spaces == "احمد"


def test_removes_spaces():
    acc = CharacterAccumulator()
    acc.add_chunk(CTCResult(characters="بسم الله", confidence=0.9))
    assert " " not in acc.normalized_no_spaces


def test_preserves_spaces_in_normalized():
    acc = CharacterAccumulator()
    acc.add_chunk(CTCResult(characters="بسم الله", confidence=0.9))
    assert " " in acc.normalized


def test_reset():
    acc = CharacterAccumulator()
    acc.add_chunk(CTCResult(characters="بسم", confidence=0.9))
    acc.reset()
    assert acc.normalized_no_spaces == ""
    assert acc.length == 0


def test_length():
    acc = CharacterAccumulator()
    acc.add_chunk(CTCResult(characters="بسم", confidence=0.9))
    assert acc.length == 3
