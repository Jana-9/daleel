import pytest

from app.core.errors import AppError
from app.services.pdf_service import extract_pages, has_text_layer, inspect_pdf
from app.services.text_normalization import clean_text
from tests.conftest import SAMPLE_PDF, make_pdf


def test_inspect_reads_page_count_and_title(sample_pdf):
    info = inspect_pdf(sample_pdf, max_pages=100)
    assert info.page_count == 4
    assert info.title == "دليل الطالب - جامعة الساحل - نموذج تجريبي"


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"", "empty_file"),
        (b"PK\x03\x04 this is a zip file", "not_pdf"),
        (b"%PDF-1.7 but then garbage", "invalid_pdf"),
    ],
)
def test_inspect_rejects_bad_files(data, code):
    with pytest.raises(AppError) as error:
        inspect_pdf(data, max_pages=100)
    assert error.value.code == code


def test_inspect_rejects_password_protected_pdf():
    with pytest.raises(AppError) as error:
        inspect_pdf(make_pdf(["secret"], password="1234"), max_pages=100)
    assert error.value.code == "encrypted_pdf"


def test_inspect_enforces_page_limit():
    with pytest.raises(AppError) as error:
        inspect_pdf(make_pdf(["a", "b", "c"]), max_pages=2)
    assert error.value.code == "too_many_pages"


def test_extract_keeps_page_numbers_and_arabic_text():
    pages = extract_pages(SAMPLE_PDF)
    assert [p.number for p in pages] == [1, 2, 3, 4]
    page_two = clean_text(" ".join(b.text for b in pages[1].blocks))
    assert "يشترط لتسجيل مقرر التدريب التعاوني" in page_two
    assert "ثمانية أسابيع متصلة" in page_two
    assert "Housing fees of 1,500 riyals" in clean_text(" ".join(b.text for b in pages[3].blocks))


def test_text_layer_detection(tmp_path):
    text_pdf = tmp_path / "text.pdf"
    text_pdf.write_bytes(make_pdf(["A page with a real text layer and enough characters."]))
    scanned_pdf = tmp_path / "scan.pdf"
    scanned_pdf.write_bytes(make_pdf(blank_pages=2))

    assert has_text_layer(extract_pages(text_pdf))
    assert not has_text_layer(extract_pages(scanned_pdf))
