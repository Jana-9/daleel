"""Text clean-up for extracted PDF text, with Arabic-specific rules.

Two levels:
- `clean_text`: safe for display. Fixes PDF extraction artefacts without changing meaning.
- `normalize_for_search`: aggressive. Used only for matching, never shown to users.
"""

import re
import unicodedata

# Arabic diacritics (harakat, tanween, shadda, sukun, superscript alef, Quranic marks).
_DIACRITICS = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭ]")
_TATWEEL = "ـ"
_ALEF_FORMS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"})
# Arabic-Indic (٠-٩) and Eastern Arabic-Indic (۰-۹) digits to 0-9.
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_INVISIBLE = re.compile("[​-‏‪-‮⁦-⁩﻿]")  # zero-width, bidi marks
_SPACES = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s]")


def clean_text(text: str) -> str:
    """Make extracted text readable and consistent, keeping its meaning and diacritics.

    NFKC is the important step for Arabic: many PDFs store "presentation forms"
    (e.g. U+FEF3 'ﻳ' instead of U+064A 'ي'), which look right but match nothing in search.
    """
    text = unicodedata.normalize("NFKC", text)
    text = _INVISIBLE.sub("", text)
    return _SPACES.sub(" ", text).strip()


def normalize_for_search(text: str) -> str:
    """Reduce text to a canonical form so different spellings of the same word match.

    "الْمُعَدَّل" / "المعدل", "إلى" / "الى", "مدرسة" / "مدرسه", "٢٫٥" / "2.5" all compare equal.
    """
    text = clean_text(text)
    text = _DIACRITICS.sub("", text).replace(_TATWEEL, "")
    text = text.translate(_ALEF_FORMS).translate(_DIGITS)
    text = text.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    text = text.replace("٫", ".").replace("،", ",")
    text = _PUNCTUATION.sub(" ", text.casefold())
    return _SPACES.sub(" ", text).strip()


def word_count(text: str) -> int:
    return len(text.split())
