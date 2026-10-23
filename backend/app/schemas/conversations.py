import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _strip(value: str) -> str:
    return " ".join(value.split())


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = _strip(value)
        if not value:
            raise ValueError("Title cannot be empty.")
        return value


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationListOut(BaseModel):
    items: list[ConversationOut]


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    marker: int
    # None when the document was deleted after the answer; the excerpt is kept.
    document_id: uuid.UUID | None
    document_title: str
    page_number: int
    excerpt: str
    # Rectangles [x0, y0, x1, y1] in PDF points (origin top-left) to highlight on the page.
    bboxes: list[list[float]]


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    status: Literal["answered", "not_found"] | None
    created_at: datetime
    sources: list[SourceOut]


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut]


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    # Limit the search to one document; by default all of the user's ready documents.
    document_id: uuid.UUID | None = None

    @field_validator("question")
    @classmethod
    def clean_question(cls, value: str) -> str:
        value = _strip(value)
        if len(value) < 2:
            raise ValueError("Question is too short.")
        return value


class AskResponse(BaseModel):
    conversation: ConversationOut
    question: MessageOut
    answer: MessageOut


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    document_id: uuid.UUID | None = None
    limit: int = Field(default=8, ge=1, le=20)


class SearchHitOut(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    page_number: int
    excerpt: str
    similarity: float
    keyword_matched: bool


class SearchOut(BaseModel):
    items: list[SearchHitOut]
