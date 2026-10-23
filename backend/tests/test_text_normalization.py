import pytest

from app.services.text_normalization import clean_text, normalize_for_search, word_count


def test_clean_text_converts_arabic_presentation_forms():
    # How many PDFs store Arabic: visually correct, but different code points.
    extracted = "ﻳﺸﺘﺮط ﻟﺘﺴﺠﻴﻞ اﻟﺘﺪرﻳﺐ"
    assert clean_text(extracted) == "يشترط لتسجيل التدريب"


def test_clean_text_collapses_whitespace_and_removes_invisible_marks():
    assert clean_text("  أتم\n 100‏  ساعة \t") == "أتم 100 ساعة"


def test_clean_text_keeps_diacritics_for_display():
    assert clean_text("الْمُعَدَّل") == "الْمُعَدَّل"


@pytest.mark.parametrize(
    ("variant", "base"),
    [
        ("الْمُعَدَّل", "المعدل"),  # diacritics
        ("الطالبــــة", "الطالبة"),  # tatweel (kashida)
        ("إلى", "الى"),  # alef with hamza below
        ("أسبوع", "اسبوع"),  # alef with hamza above
        ("آخر", "اخر"),  # alef madda
        ("مدرسة", "مدرسه"),  # ta marbuta
        ("على", "علي"),  # alef maqsura
        ("٢٫٥", "2.5"),  # Arabic-Indic digits and decimal separator
        ("Housing FEES", "housing fees"),  # case
    ],
)
def test_normalize_for_search_treats_spelling_variants_as_equal(variant, base):
    assert normalize_for_search(variant) == normalize_for_search(base)


def test_normalize_for_search_drops_punctuation():
    assert normalize_for_search("المادة الرابعة - شروط التسجيل:") == "الماده الرابعه شروط التسجيل"


def test_word_count():
    assert word_count("يشترط أن يكون الطالب قد أتم 100 ساعة") == 8
