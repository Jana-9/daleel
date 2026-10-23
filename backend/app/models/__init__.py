"""Import every model here so Alembic autogenerate can see them."""

from app.models.document import (
    Document,
    DocumentChunk,
    DocumentStatus,
    JobStatus,
    ProcessingJob,
)
from app.models.user import User

__all__ = ["Document", "DocumentChunk", "DocumentStatus", "JobStatus", "ProcessingJob", "User"]
