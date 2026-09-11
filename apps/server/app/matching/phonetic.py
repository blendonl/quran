import panphon.distance

PHONETIC_GROUPS = [
    "سصث",
    "حخ",
    "تط",
    "دض",
    "ذظز",
    "قك",
    "بم",
    "واي",
]

_PHONETIC_MAP: dict[str, frozenset[str]] = {}
for _group in PHONETIC_GROUPS:
    group_set = frozenset(_group)
    for _ch in _group:
        if _ch in _PHONETIC_MAP:
            _PHONETIC_MAP[_ch] = _PHONETIC_MAP[_ch] | group_set
        else:
            _PHONETIC_MAP[_ch] = group_set


ARABIC_TO_IPA: dict[str, str] = {
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
    "ء": "ʔ",
    "ا": "aː",
}

_distance_calc = panphon.distance.Distance()
_ipa_distance_cache: dict[tuple[str, str], float] = {}

MAX_FEATURE_DISTANCE = 16.0


def ipa_distance(a: str, b: str) -> float:
    if a == b:
        return 0.0

    cache_key = (a, b) if a <= b else (b, a)
    if cache_key in _ipa_distance_cache:
        return _ipa_distance_cache[cache_key]

    ipa_a = ARABIC_TO_IPA.get(a, a)
    ipa_b = ARABIC_TO_IPA.get(b, b)

    if ipa_a == ipa_b:
        _ipa_distance_cache[cache_key] = 0.0
        return 0.0

    try:
        raw = _distance_calc.weighted_feature_edit_distance(ipa_a, ipa_b)
        normalized = min(raw / MAX_FEATURE_DISTANCE, 1.0)
    except Exception:
        normalized = 1.0

    _ipa_distance_cache[cache_key] = normalized
    return normalized


def phonetic_similar(a: str, b: str, threshold: float = 0.3) -> bool:
    return ipa_distance(a, b) <= threshold


def phonetic_key(ch: str) -> frozenset[str]:
    return _PHONETIC_MAP.get(ch, frozenset({ch}))


def phonetic_match(a: str, b: str) -> bool:
    if a == b:
        return True
    key_a = _PHONETIC_MAP.get(a)
    key_b = _PHONETIC_MAP.get(b)
    if key_a is None or key_b is None:
        return False
    return bool(key_a & key_b)


def to_phonetic(text: str) -> str:
    result = []
    for ch in text:
        groups = _PHONETIC_MAP.get(ch)
        if groups:
            result.append(min(groups))
        else:
            result.append(ch)
    return "".join(result)
