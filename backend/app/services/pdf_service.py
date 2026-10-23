"""PDF validation (at upload time) and text extraction (in the worker), using PyMuPDF."""

from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.core.errors import AppError
from app.services.chunking import Page, TextBlock
from app.services.text_normalization import clean_text

PDF_MAGIC = b"%PDF-"
# A page with fewer extracted characters than this is treated as having no real text layer.
MIN_CHARS_PER_TEXT_PAGE = 20


@dataclass(frozen=True)
class PdfInfo:
    page_count: int
    title: str | None


def inspect_pdf(data: bytes, *, max_pages: int) -> PdfInfo:
    """Check that `data` is a PDF we can process. Raises AppError with a stable code if not."""
    if not data:
        raise AppError(422, "empty_file", "The file is empty.")
    # Check the content, not the filename or the browser's content type: both can lie.
    if not data[:1024].lstrip().startswith(PDF_MAGIC):
        raise AppError(422, "not_pdf", "Only PDF files are supported.")
    try:
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            if doc.needs_pass:
                raise AppError(422, "encrypted_pdf", "Password-protected PDFs are not supported.")
            if doc.page_count == 0:
                raise AppError(422, "empty_file", "The PDF has no pages.")
            if doc.page_count > max_pages:
                raise AppError(422, "too_many_pages", f"The PDF has more than {max_pages} pages.")
            title = clean_text((doc.metadata or {}).get("title") or "") or None
            return PdfInfo(page_count=doc.page_count, title=title)
    except AppError:
        raise
    except Exception as exc:  # PyMuPDF raises various errors for damaged files
        raise AppError(422, "invalid_pdf", "The PDF could not be read.") from exc


def extract_pages(path: Path) -> list[Page]:
    """Text blocks with their positions, page by page, in reading order."""
    pages: list[Page] = []
    with pymupdf.open(path) as doc:
        for index, page in enumerate(doc):
            blocks = [
                TextBlock(text=block[4], bbox=(block[0], block[1], block[2], block[3]))
                # block = (x0, y0, x1, y1, text, block_no, block_type); type 0 is text, 1 image
                for block in page.get_text("blocks", sort=False)
                if block[6] == 0 and block[4].strip()
            ]
            pages.append(Page(number=index + 1, blocks=blocks))
    return pages


def has_text_layer(pages: list[Page]) -> bool:
    """False for scanned PDFs (images of text), which need OCR that Daleel does not do yet."""
    text_pages = sum(
        1
        for page in pages
        if sum(len(clean_text(b.text)) for b in page.blocks) >= MIN_CHARS_PER_TEXT_PAGE
    )
    return text_pages > 0 and text_pages >= len(pages) / 2
