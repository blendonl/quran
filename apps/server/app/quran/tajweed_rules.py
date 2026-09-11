from dataclasses import dataclass
from enum import Enum

from app.quran.qiraat import QiraahConfig


class TajweedRule(Enum):
    IDGHAAM_BI_GHUNNAH = "idghaam_bi_ghunnah"
    IDGHAAM_BILA_GHUNNAH = "idghaam_bila_ghunnah"
    IKHFAA = "ikhfaa"
    IQLAB = "iqlab"
    IZHAR = "izhar"
    MADD_NATURAL = "madd_natural"
    MADD_CONNECTED = "madd_connected"
    MADD_SEPARATED = "madd_separated"
    MADD_SECONDARY = "madd_secondary"
    GHUNNAH = "ghunnah"
    QALQALAH = "qalqalah"


IDGHAAM_GHUNNAH_LETTERS = frozenset("ينمو")
IDGHAAM_NO_GHUNNAH_LETTERS = frozenset("لر")

SUKUN = "\u0652"
SHADDA = "\u0651"
FATHATAN = "\u064B"
DAMMATAN = "\u064C"
KASRATAN = "\u064D"
FATHA = "\u064E"
DAMMA = "\u064F"
KASRA = "\u0650"

TANWEEN_MARKS = frozenset({FATHATAN, DAMMATAN, KASRATAN})
VOWEL_MARKS = frozenset({FATHA, DAMMA, KASRA})
MADD_LETTERS = frozenset("اوي")

NOON = "ن"
MEEM = "م"


@dataclass
class TajweedAnnotation:
    rule: TajweedRule
    word_index: int
    letter_index: int
    extends_to_next_word: bool = False


def detect_tajweed_rules(
    words: list[str],
    qiraah: QiraahConfig,
) -> list[TajweedAnnotation]:
    annotations: list[TajweedAnnotation] = []
    flat_chars = _flatten_words(words)

    for pos, (ch, diacritics, word_idx, letter_idx) in enumerate(flat_chars):
        next_base = _next_base_char(flat_chars, pos)

        if _has_noon_sakin_or_tanween(ch, diacritics):
            annotation = _check_noon_rules(
                ch, diacritics, next_base, word_idx, letter_idx, qiraah, flat_chars, pos,
            )
            if annotation:
                annotations.append(annotation)

        if ch == MEEM and _is_sakin(diacritics) and next_base:
            next_ch, _, next_wi, _ = next_base
            if next_ch == MEEM:
                annotations.append(TajweedAnnotation(
                    rule=TajweedRule.GHUNNAH,
                    word_index=word_idx,
                    letter_index=letter_idx,
                ))

        if SHADDA in diacritics and ch in qiraah.ghunnah_letters:
            annotations.append(TajweedAnnotation(
                rule=TajweedRule.GHUNNAH,
                word_index=word_idx,
                letter_index=letter_idx,
            ))

        if ch in qiraah.qalqalah_letters and _is_sakin(diacritics):
            annotations.append(TajweedAnnotation(
                rule=TajweedRule.QALQALAH,
                word_index=word_idx,
                letter_index=letter_idx,
            ))

        madd = _check_madd(flat_chars, pos, qiraah)
        if madd:
            annotations.append(madd)

    return annotations


@dataclass
class _FlatChar:
    char: str
    diacritics: str
    word_index: int
    letter_index: int


def _flatten_words(words: list[str]) -> list[tuple[str, str, int, int]]:
    result: list[tuple[str, str, int, int]] = []
    for word_idx, word in enumerate(words):
        letter_idx = 0
        i = 0
        chars = list(word)
        while i < len(chars):
            ch = chars[i]
            if _is_tashkeel(ch):
                i += 1
                continue
            diacritics = ""
            j = i + 1
            while j < len(chars) and _is_tashkeel(chars[j]):
                diacritics += chars[j]
                j += 1
            result.append((ch, diacritics, word_idx, letter_idx))
            letter_idx += 1
            i = j
    return result


def _is_tashkeel(ch: str) -> bool:
    return "\u064B" <= ch <= "\u0652" or ch == "\u0670" or ch == "\u0640"


def _is_sakin(diacritics: str) -> bool:
    return SUKUN in diacritics or (
        not any(m in diacritics for m in VOWEL_MARKS | TANWEEN_MARKS | {SHADDA})
    )


def _has_noon_sakin_or_tanween(ch: str, diacritics: str) -> bool:
    if ch == NOON and _is_sakin(diacritics):
        return True
    return bool(TANWEEN_MARKS & set(diacritics))


def _next_base_char(
    flat_chars: list[tuple[str, str, int, int]], pos: int,
) -> tuple[str, str, int, int] | None:
    if pos + 1 < len(flat_chars):
        return flat_chars[pos + 1]
    return None


def _check_noon_rules(
    ch: str,
    diacritics: str,
    next_base: tuple[str, str, int, int] | None,
    word_idx: int,
    letter_idx: int,
    qiraah: QiraahConfig,
    flat_chars: list[tuple[str, str, int, int]],
    pos: int,
) -> TajweedAnnotation | None:
    if not next_base:
        return None

    next_ch, next_diacritics, next_wi, _ = next_base
    extends = next_wi != word_idx

    if next_ch in IDGHAAM_GHUNNAH_LETTERS and extends:
        return TajweedAnnotation(
            rule=TajweedRule.IDGHAAM_BI_GHUNNAH,
            word_index=word_idx,
            letter_index=letter_idx,
            extends_to_next_word=True,
        )

    if next_ch in IDGHAAM_NO_GHUNNAH_LETTERS and extends:
        return TajweedAnnotation(
            rule=TajweedRule.IDGHAAM_BILA_GHUNNAH,
            word_index=word_idx,
            letter_index=letter_idx,
            extends_to_next_word=True,
        )

    if next_ch == qiraah.iqlab_letter:
        return TajweedAnnotation(
            rule=TajweedRule.IQLAB,
            word_index=word_idx,
            letter_index=letter_idx,
            extends_to_next_word=extends,
        )

    if next_ch in qiraah.ikhfaa_letters:
        return TajweedAnnotation(
            rule=TajweedRule.IKHFAA,
            word_index=word_idx,
            letter_index=letter_idx,
            extends_to_next_word=extends,
        )

    if next_ch in qiraah.izhar_letters:
        return TajweedAnnotation(
            rule=TajweedRule.IZHAR,
            word_index=word_idx,
            letter_index=letter_idx,
            extends_to_next_word=extends,
        )

    return None


def _check_madd(
    flat_chars: list[tuple[str, str, int, int]],
    pos: int,
    qiraah: QiraahConfig,
) -> TajweedAnnotation | None:
    ch, diacritics, word_idx, letter_idx = flat_chars[pos]

    if ch not in MADD_LETTERS:
        return None

    if pos == 0:
        return None

    prev_ch, prev_diacritics, _, _ = flat_chars[pos - 1]

    is_madd_letter = False
    if ch == "ا" and FATHA in prev_diacritics:
        is_madd_letter = True
    elif ch == "و" and DAMMA in prev_diacritics:
        is_madd_letter = True
    elif ch == "ي" and KASRA in prev_diacritics:
        is_madd_letter = True

    if not is_madd_letter:
        return None

    next_base = _next_base_char(flat_chars, pos)
    if not next_base:
        return TajweedAnnotation(
            rule=TajweedRule.MADD_NATURAL,
            word_index=word_idx,
            letter_index=letter_idx,
        )

    next_ch, next_diacritics, next_wi, _ = next_base
    if next_ch == "ء" or next_ch == "\u0621":
        if next_wi == word_idx:
            return TajweedAnnotation(
                rule=TajweedRule.MADD_CONNECTED,
                word_index=word_idx,
                letter_index=letter_idx,
            )
        else:
            return TajweedAnnotation(
                rule=TajweedRule.MADD_SEPARATED,
                word_index=word_idx,
                letter_index=letter_idx,
                extends_to_next_word=True,
            )

    if SHADDA in next_diacritics or SUKUN in next_diacritics:
        return TajweedAnnotation(
            rule=TajweedRule.MADD_SECONDARY,
            word_index=word_idx,
            letter_index=letter_idx,
        )

    return TajweedAnnotation(
        rule=TajweedRule.MADD_NATURAL,
        word_index=word_idx,
        letter_index=letter_idx,
    )
