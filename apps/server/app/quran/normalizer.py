import re
import unicodedata

TASHKEEL_PATTERN = re.compile(r"[\u064B-\u0652\u0670\u0640]")

HAMZA_MAP = {
    "\u0622": "\u0627",  # آ → ا
    "\u0623": "\u0627",  # أ → ا
    "\u0625": "\u0627",  # إ → ا
    "\u0671": "\u0627",  # ٱ → ا
}

TA_MARBUTA = "\u0629"  # ة
HA = "\u0647"  # ه

ALEF_MAKSURA = "\u0649"  # ى
YA = "\u064A"  # ي


def normalize(text: str) -> str:
    result = strip_tashkeel(text)
    result = normalize_hamza(result)
    result = result.replace(TA_MARBUTA, HA)
    result = result.replace(ALEF_MAKSURA, YA)
    result = re.sub(r"\s+", " ", result).strip()
    return result


def strip_tashkeel(text: str) -> str:
    return TASHKEEL_PATTERN.sub("", text)


def normalize_hamza(text: str) -> str:
    for src, dst in HAMZA_MAP.items():
        text = text.replace(src, dst)
    return text


def split_words(text: str) -> list[str]:
    return [w for w in normalize(text).split() if w]
