from dataclasses import dataclass

from app.quran.tajweed_rules import (
    TajweedAnnotation,
    TajweedRule,
    detect_tajweed_rules,
    _flatten_words,
    _is_tashkeel,
    SHADDA,
    FATHA,
    DAMMA,
    KASRA,
    FATHATAN,
    DAMMATAN,
    KASRATAN,
    SUKUN,
)
from app.quran.qiraat import QiraahConfig, HAFS_CONFIG


ARABIC_TO_IPA: dict[str, str] = {
    "ء": "ʔ",
    "ب": "b",
    "ت": "t",
    "ث": "θ",
    "ج": "dʒ",
    "ح": "ħ",
    "خ": "x",
    "د": "d",
    "ذ": "ð",
    "ر": "r",
    "ز": "z",
    "س": "s",
    "ش": "ʃ",
    "ص": "sˤ",
    "ض": "dˤ",
    "ط": "tˤ",
    "ظ": "ðˤ",
    "ع": "ʕ",
    "غ": "ɣ",
    "ف": "f",
    "ق": "q",
    "ك": "k",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ه": "h",
    "و": "w",
    "ي": "j",
    "ة": "h",
    "ى": "aː",
    "ٱ": "ʔ",
    "آ": "ʔaː",
    "أ": "ʔ",
    "إ": "ʔ",
    "ؤ": "ʔ",
    "ئ": "ʔ",
}

VOWEL_IPA = {
    FATHA: "a",
    DAMMA: "u",
    KASRA: "i",
    FATHATAN: "an",
    DAMMATAN: "un",
    KASRATAN: "in",
}

MADD_VOWELS = {
    "ا": "aː",
    "و": "uː",
    "ي": "iː",
}


@dataclass
class IPAUnit:
    ipa: str
    arabic_word_index: int
    arabic_letter_index: int
    tajweed_rule: str | None = None
    is_geminated: bool = False
    madd_type: str | None = None


def convert_ayah_to_ipa(
    words: list[str],
    qiraah: QiraahConfig = HAFS_CONFIG,
) -> list[IPAUnit]:
    annotations = detect_tajweed_rules(words, qiraah)
    annotation_map: dict[tuple[int, int], TajweedAnnotation] = {
        (a.word_index, a.letter_index): a for a in annotations
    }

    flat_chars = _flatten_words(words)
    units: list[IPAUnit] = []

    for pos, (ch, diacritics, word_idx, letter_idx) in enumerate(flat_chars):
        annotation = annotation_map.get((word_idx, letter_idx))
        tajweed_rule = annotation.rule.value if annotation else None

        is_geminated = SHADDA in diacritics
        base_ipa = ARABIC_TO_IPA.get(ch, ch)

        madd_type = None
        if annotation and annotation.rule in (
            TajweedRule.MADD_NATURAL,
            TajweedRule.MADD_CONNECTED,
            TajweedRule.MADD_SEPARATED,
            TajweedRule.MADD_SECONDARY,
        ):
            madd_type = annotation.rule.value
            ipa_str = MADD_VOWELS.get(ch, base_ipa)
        elif _is_madd_letter_in_context(flat_chars, pos):
            ipa_str = MADD_VOWELS.get(ch, base_ipa)
            madd_type = "madd_natural"
        else:
            ipa_str = base_ipa

        if annotation and annotation.rule == TajweedRule.IQLAB:
            ipa_str = base_ipa + _get_vowel_ipa(diacritics) + "m"
            units.append(IPAUnit(
                ipa=ipa_str,
                arabic_word_index=word_idx,
                arabic_letter_index=letter_idx,
                tajweed_rule=tajweed_rule,
                is_geminated=is_geminated,
            ))
            continue

        if annotation and annotation.rule in (
            TajweedRule.IDGHAAM_BI_GHUNNAH,
            TajweedRule.IDGHAAM_BILA_GHUNNAH,
        ):
            vowel_ipa = _get_vowel_ipa(diacritics)
            ipa_str = vowel_ipa if vowel_ipa else ""
            units.append(IPAUnit(
                ipa=ipa_str,
                arabic_word_index=word_idx,
                arabic_letter_index=letter_idx,
                tajweed_rule=tajweed_rule,
                is_geminated=is_geminated,
            ))
            continue

        vowel_ipa = _get_vowel_ipa(diacritics)
        if is_geminated:
            ipa_str = ipa_str + ipa_str + vowel_ipa
        else:
            ipa_str = ipa_str + vowel_ipa

        units.append(IPAUnit(
            ipa=ipa_str,
            arabic_word_index=word_idx,
            arabic_letter_index=letter_idx,
            tajweed_rule=tajweed_rule,
            is_geminated=is_geminated,
            madd_type=madd_type,
        ))

    return units


def _get_vowel_ipa(diacritics: str) -> str:
    for mark, ipa in VOWEL_IPA.items():
        if mark in diacritics:
            return ipa
    return ""


def _is_madd_letter_in_context(
    flat_chars: list[tuple[str, str, int, int]], pos: int,
) -> bool:
    ch, diacritics, _, _ = flat_chars[pos]
    if ch not in MADD_VOWELS:
        return False
    if pos == 0:
        return False

    prev_ch, prev_diacritics, _, _ = flat_chars[pos - 1]
    if ch == "ا" and FATHA in prev_diacritics:
        return True
    if ch == "و" and DAMMA in prev_diacritics:
        return True
    if ch == "ي" and KASRA in prev_diacritics:
        return True
    return False


def ayah_ipa_to_string(units: list[IPAUnit]) -> str:
    return "".join(u.ipa for u in units)
