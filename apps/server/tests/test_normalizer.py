from app.quran.normalizer import normalize, strip_tashkeel, normalize_hamza, split_words


def test_strip_tashkeel():
    assert strip_tashkeel("بِسْمِ") == "بسم"
    assert strip_tashkeel("ٱلرَّحْمَٰنِ") == "ٱلرحمن"


def test_normalize_hamza():
    assert normalize_hamza("أحمد") == "احمد"
    assert normalize_hamza("إسلام") == "اسلام"
    assert normalize_hamza("ٱللَّهِ") == "اللَّهِ"


def test_normalize_full():
    assert normalize("بِسْمِ ٱللَّهِ") == "بسم الله"
    assert normalize("ٱلرَّحْمَٰنِ ٱلرَّحِيمِ") == "الرحمن الرحيم"


def test_ta_marbuta_normalization():
    assert normalize("رَحْمَةٌ") == "رحمه"


def test_alef_maksura_normalization():
    assert normalize("مُوسَى") == "موسي"


def test_split_words():
    words = split_words("بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ")
    assert len(words) == 4
    assert words[0] == "بسم"
    assert words[1] == "الله"


def test_split_words_empty():
    assert split_words("") == []
    assert split_words("   ") == []
