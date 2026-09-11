import unicodedata


LETTER_NAMES = {
    "ا": "الف",
    "ل": "لام",
    "م": "ميم",
    "ص": "صاد",
    "ر": "را",
    "ك": "كاف",
    "ه": "ها",
    "ي": "يا",
    "ع": "عين",
    "ط": "طا",
    "س": "سين",
    "ح": "حا",
    "ق": "قاف",
    "ن": "نون",
}

MUQATTAAT_LETTERS = frozenset(LETTER_NAMES.keys())

MAX_MUQATTAAT_LENGTH = 6


def _base_letters(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def is_muqattaat(normalized_text_no_spaces: str) -> bool:
    letters = _base_letters(normalized_text_no_spaces)
    if not letters or len(letters) > MAX_MUQATTAAT_LENGTH:
        return False
    return all(ch in MUQATTAAT_LETTERS for ch in letters)


def spelled_out(normalized_text_no_spaces: str) -> str | None:
    letters = _base_letters(normalized_text_no_spaces)
    if not letters or len(letters) > MAX_MUQATTAAT_LENGTH:
        return None
    if not all(ch in MUQATTAAT_LETTERS for ch in letters):
        return None
    return "".join(LETTER_NAMES[ch] for ch in letters)
