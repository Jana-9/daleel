"""Data access for documents, their processing jobs and chunks.

Every read that serves a user takes `owner_id`, so ownership is enforced in the query itself
rather than checked afterwards.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk, JobStatus, ProcessingJob


def create(db: Session, document: Document) -> Document:
    db.add(document)
    db.flush()
    return document


def get_owned(db: Session, document_id: uuid.UUID, owner_id: uuid.UUID) -> Document | None:
    return db.scalar(
        select(Document).where(Document.id == document_id, Document.owner_id == owner_id)
    )


def list_owned(db: Session, owner_id: uuid.UUID) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.desc(), Document.id)
        )
    )


def chunk_counts(db: Session, document_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not document_ids:
        return {}
    rows = db.execute(
        select(DocumentChunk.document_id, func.count())
        .where(DocumentChunk.document_id.in_(document_ids))
        .group_by(DocumentChunk.document_id)
    )
    return {document_id: count for document_id, count in rows}


def enqueue_job(db: Session, document_id: uuid.UUID) -> ProcessingJob:
    job = ProcessingJob(document_id=document_id, status=JobStatus.QUEUED)
    db.add(job)
    db.flush()
    return job


def claim_next_job(db: Session) -> uuid.UUID | None:
    """Atomically take the oldest queued job and mark it running.

    FOR UPDATE SKIP LOCKED makes this safe with several workers: a row locked by one worker
    is skipped by the others instead of being processed twice or blocking them.
    """
    return db.scalar(
        text(
            """
            UPDATE processing_jobs
            SET status = :running, attempts = attempts + 1, locked_at = now(),
                started_at = COALESCE(started_at, now())
            WHERE id = (
                SELECT id FROM processing_jobs
                WHERE status = :queued
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING id
            """
        ),
        {"running": JobStatus.RUNNING.value, "queued": JobStatus.QUEUED.value},
    )


def requeue_stale_jobs(db: Session, older_than: timedelta) -> int:
    """Put back jobs whose worker died mid-way (still 'running' long after being locked)."""
    cutoff = datetime.now(UTC) - older_than
    result = db.execute(
        update(ProcessingJob)
        .where(ProcessingJob.status == JobStatus.RUNNING, ProcessingJob.locked_at < cutoff)
        .values(status=JobStatus.QUEUED, locked_at=None)
    )
    return result.rowcount or 0


def replace_chunks(db: Session, document_id: uuid.UUID, chunks: list[DocumentChunk]) -> None:
    """Delete then insert, in the caller's transaction: retries never leave duplicates."""
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    db.add_all(chunks)
