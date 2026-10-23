"""The document processing pipeline and the worker loop that runs it.

    queued job -> claim (SKIP LOCKED) -> extract -> check text layer -> chunk -> embed
               -> save chunks + mark READY (one transaction)

Expensive work (extraction, embedding) happens outside any database transaction; the
final write is a single short transaction, so a crash at any point leaves the document either
untouched or fully processed, never half-indexed.
"""

import logging
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.document import Document, DocumentChunk, DocumentStatus, JobStatus, ProcessingJob
from app.repositories import documents as documents_repo
from app.services.chunking import chunk_document
from app.services.embeddings import EmbeddingError, get_embedding_provider
from app.services.pdf_service import extract_pages, has_text_layer
from app.services.storage_service import get_storage
from app.services.text_normalization import normalize_for_search, word_count

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """A failure with a user-facing code. `permanent` failures are not retried automatically."""

    def __init__(self, code: str, detail: str = "", *, permanent: bool) -> None:
        super().__init__(detail or code)
        self.code = code
        self.permanent = permanent


def _build_chunks(document: Document, path) -> list[DocumentChunk]:
    settings = get_settings()
    try:
        pages = extract_pages(path)
    except Exception as exc:
        raise ProcessingError("extraction_failed", repr(exc), permanent=True) from exc
    if not has_text_layer(pages):
        raise ProcessingError("scanned_pdf", permanent=True)

    drafts = chunk_document(pages, settings.chunk_size, settings.chunk_overlap)
    if not drafts:
        raise ProcessingError("no_text", permanent=True)

    provider = get_embedding_provider()
    try:
        vectors = provider.embed_documents([d.content for d in drafts])
    except EmbeddingError as exc:
        raise ProcessingError("embedding_failed", str(exc), permanent=False) from exc

    return [
        DocumentChunk(
            document_id=document.id,
            chunk_index=index,
            page_number=draft.page_number,
            content=draft.content,
            content_normalized=normalize_for_search(draft.content),
            word_count=word_count(draft.content),
            bboxes=[[round(v, 2) for v in rect] for rect in draft.bboxes],
            embedding=vector,
            embedding_model=provider.model_name,
        )
        for index, (draft, vector) in enumerate(zip(drafts, vectors, strict=True))
    ]


def _claim() -> uuid.UUID | None:
    with SessionLocal() as db, db.begin():
        job_id = documents_repo.claim_next_job(db)
        if job_id is not None:
            job = db.get(ProcessingJob, job_id)
            job.document.status = DocumentStatus.PROCESSING
        return job_id


def _finish(job_id: uuid.UUID, started: float, *, chunks=None, error=None) -> None:
    """Write the outcome. Locks the job row, so it sees whether the document was deleted."""
    settings = get_settings()
    with SessionLocal() as db, db.begin():
        job = db.scalar(select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update())
        if job is None:
            logger.info("document deleted during processing", extra={"job_id": str(job_id)})
            return
        document = job.document
        now = datetime.now(UTC)
        job.locked_at = None
        job.duration_ms = int((time.monotonic() - started) * 1000)

        if error is None:
            documents_repo.replace_chunks(db, document.id, chunks)
            job.status, job.finished_at = JobStatus.DONE, now
            document.status, document.error_code, document.processed_at = (
                DocumentStatus.READY,
                None,
                now,
            )
            return

        job.error_code, job.error_detail = error.code, str(error)[:2000]
        if not error.permanent and job.attempts < settings.job_max_attempts:
            job.status = JobStatus.QUEUED  # try again on a later loop
            document.status = DocumentStatus.UPLOADED
        else:
            job.status, job.finished_at = JobStatus.FAILED, now
            document.status, document.error_code = DocumentStatus.FAILED, error.code


def process_next_job() -> bool:
    """Claim and process one job. Returns False when there was nothing to do."""
    job_id = _claim()
    if job_id is None:
        return False

    started = time.monotonic()
    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id)
        document = job.document if job else None
        path = get_storage().path(document.storage_key) if document else None
    if document is None:
        return True

    try:
        chunks = _build_chunks(document, path)
    except ProcessingError as exc:
        logger.warning("processing failed: %s", exc.code, extra={"job_id": str(job_id)})
        _finish(job_id, started, error=exc)
    except Exception as exc:  # unexpected bug: record it, retry a limited number of times
        logger.exception("unexpected processing error", extra={"job_id": str(job_id)})
        _finish(
            job_id, started, error=ProcessingError("internal_error", repr(exc), permanent=False)
        )
    else:
        _finish(job_id, started, chunks=chunks)
        logger.info("document ready: %d chunks", len(chunks), extra={"job_id": str(job_id)})
    return True


def requeue_stale_jobs() -> int:
    with SessionLocal() as db, db.begin():
        minutes = get_settings().job_stale_minutes
        return documents_repo.requeue_stale_jobs(db, timedelta(minutes=minutes))


def run_worker(stop: threading.Event) -> None:
    """Loop until `stop` is set: process jobs back to back, sleep when the queue is empty."""
    settings = get_settings()
    logger.info("worker started")
    last_stale_check = 0.0
    while not stop.is_set():
        try:
            if time.monotonic() - last_stale_check > 60:
                if count := requeue_stale_jobs():
                    logger.warning("requeued %d stale jobs", count)
                last_stale_check = time.monotonic()
            if not process_next_job():
                stop.wait(settings.worker_poll_seconds)
        except Exception:
            # e.g. the database is briefly unreachable: log, wait, keep the worker alive
            logger.exception("worker loop error")
            stop.wait(settings.worker_poll_seconds)
    logger.info("worker stopped")
