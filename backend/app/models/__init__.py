"""Import every model here so Alembic autogenerate can see them."""

from app.models.conversation import (
    AnswerStatus,
    Conversation,
    Message,
    MessageRole,
    MessageSource,
)
from app.models.document import (
    Document,
    DocumentChunk,
    DocumentStatus,
    JobStatus,
    ProcessingJob,
)
from app.models.user import User

__all__ = [
    "AnswerStatus",
    "Conversation",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "JobStatus",
    "Message",
    "MessageRole",
    "MessageSource",
    "ProcessingJob",
    "User",
]
