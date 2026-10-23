"""Split extracted pages into overlapping passages ("chunks") for embedding and search.

Rules:
- A chunk never crosses a page boundary, so every chunk has exactly one page number to cite.
- Chunks are built from whole text blocks (lines/paragraphs from the PDF), so each chunk knows
  the rectangles it came from and the viewer can highlight it.
- A block longer than the chunk size is split at sentence, then word, boundaries.
- Consecutive chunks on a page share trailing blocks up to `overlap` characters, so a sentence
  cut at a chunk edge still appears whole in one of them.
"""

import re
from dataclasses import dataclass, field

from app.services.text_normalization import clean_text

Rect = tuple[float, float, float, float]


@dataclass(frozen=True)
class TextBlock:
    text: str
    bbox: Rect


@dataclass(frozen=True)
class Page:
    number: int  # 1-based
    blocks: list[TextBlock]


@dataclass
class ChunkDraft:
    page_number: int
    texts: list[str] = field(default_factory=list)
    bboxes: list[Rect] = field(default_factory=list)

    @property
    def content(self) -> str:
        return " ".join(self.texts)

    @property
    def length(self) -> int:
        return len(self.content)


_SENTENCE_END = re.compile(r"(?<=[.!?؟؛])\s+")


def _split_long_text(text: str, size: int) -> list[str]:
    """Split text longer than `size` at sentence ends, falling back to word boundaries."""
    pieces: list[str] = []
    current = ""
    for sentence in _SENTENCE_END.split(text):
        for word in sentence.split(" ") if len(sentence) > size else [sentence]:
            candidate = f"{current} {word}".strip()
            if len(candidate) > size and current:
                pieces.append(current)
                current = word
            else:
                current = candidate
    if current:
        pieces.append(current)
    return pieces


def _units(page: Page, size: int) -> list[TextBlock]:
    """The page's blocks, cleaned, with empty ones dropped and long ones split."""
    units: list[TextBlock] = []
    for block in page.blocks:
        text = clean_text(block.text)
        if not text:
            continue
        if len(text) <= size:
            units.append(TextBlock(text, block.bbox))
        else:
            units.extend(TextBlock(piece, block.bbox) for piece in _split_long_text(text, size))
    return units


def chunk_page(page: Page, size: int, overlap: int) -> list[ChunkDraft]:
    chunks: list[ChunkDraft] = []
    current = ChunkDraft(page.number)
    new_units_in_current = 0  # units added since the overlap carried over

    for unit in _units(page, size):
        would_be = current.length + len(unit.text) + (1 if current.texts else 0)
        if current.texts and would_be > size and new_units_in_current > 0:
            chunks.append(current)
            current = _carry_overlap(current, overlap)
            new_units_in_current = 0
        current.texts.append(unit.text)
        current.bboxes.append(unit.bbox)
        new_units_in_current += 1

    if new_units_in_current > 0:
        chunks.append(current)
    return chunks


def _carry_overlap(previous: ChunkDraft, overlap: int) -> ChunkDraft:
    """Start a new chunk with the last blocks of `previous`, up to `overlap` characters."""
    carried = ChunkDraft(previous.page_number)
    total = 0
    for text, bbox in zip(reversed(previous.texts), reversed(previous.bboxes), strict=True):
        if total + len(text) > overlap:
            break
        carried.texts.insert(0, text)
        carried.bboxes.insert(0, bbox)
        total += len(text) + 1
    return carried


def chunk_document(pages: list[Page], size: int, overlap: int) -> list[ChunkDraft]:
    """Chunks for all pages, in reading order. Their position in the list is the chunk index."""
    return [chunk for page in pages for chunk in chunk_page(page, size, overlap)]
