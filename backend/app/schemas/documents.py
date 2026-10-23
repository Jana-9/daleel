import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

DocumentStatusLiteral = Literal["uploaded", "processing", "ready", "failed"]


class DocumentOut(BaseModel):
    id: uuid.UUID
    title: str
    original_filename: str
    file_size: int
    page_count: int
    status: DocumentStatusLiteral
    # Set when status is "failed": scanned_pdf, no_text, extraction_failed,
    # embedding_failed or internal_error.
    error_code: str | None
    chunk_count: int
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None


class DocumentListOut(BaseModel):
    items: list[DocumentOut]
