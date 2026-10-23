"""Rules for uploading, listing, deleting and retrying documents."""

import logging
import uuid
from pathlib import PurePath

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.repositories import documents as documents_repo
from app.schemas.documents import DocumentOut
from app.services.pdf_service import inspect_pdf
from app.services.storage_service import Storage, make_key
from app.services.text_normalization import clean_text

logger = logging.getLogger(__name__)


def _not_found() -> AppError:
    # Same response whether the document does not exist or belongs to someone else,
    # so IDs of other users' documents cannot be discovered.
    return AppError(404, "document_not_found", "Document not found.")


def _safe_filename(filename: str | None) -> str:
    """The user's filename is only ever displayed, never used as a path."""
    name = clean_text(PurePath(filename or "").name)[:255]
    return name or "document.pdf"


def _title_from(filename: str, pdf_title: str | None) -> str:
    stem = filename[:-4] if filename.lower().endswith(".pdf") else filename
    return (pdf_title or stem or "Untitled")[:255]


def to_out(document: Document, chunk_count: int) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        title=document.title,
        original_filename=document.original_filename,
        file_size=document.file_size,
        page_count=document.page_count,
        status=document.status,
        error_code=document.error_code,
        chunk_count=chunk_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
        processed_at=document.processed_at,
    )


def upload(
    db: Session, storage: Storage, owner: User, filename: str | None, data: bytes
) -> DocumentOut:
    settings = get_settings()
    if len(data) > settings.max_upload_bytes:
        raise AppError(
            413, "file_too_large", f"The file is larger than {settings.max_upload_mb} MB."
        )
    info = inspect_pdf(data, max_pages=settings.max_pages)

    name = _safe_filename(filename)
    document_id = uuid.uuid4()
    key = make_key(owner.id, document_id)
    storage.save(key, data)
    try:
        document = documents_repo.create(
            db,
            Document(
                id=document_id,
                owner_id=owner.id,
                title=_title_from(name, info.title),
                original_filename=name,
                storage_key=key,
                mime_type="application/pdf",
                file_size=len(data),
                page_count=info.page_count,
                status=DocumentStatus.UPLOADED,
            ),
        )
        # Document and job are committed together: a stored document always has a job.
        documents_repo.enqueue_job(db, document.id)
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(key)  # do not leave an orphan file behind
        raise
    db.refresh(document)
    logger.info("document uploaded", extra={"document_id": str(document.id)})
    return to_out(document, chunk_count=0)


def list_documents(db: Session, owner: User) -> list[DocumentOut]:
    documents = documents_repo.list_owned(db, owner.id)
    counts = documents_repo.chunk_counts(db, [d.id for d in documents])
    return [to_out(d, counts.get(d.id, 0)) for d in documents]


def get_document(db: Session, owner: User, document_id: uuid.UUID) -> Document:
    document = documents_repo.get_owned(db, document_id, owner.id)
    if document is None:
        raise _not_found()
    return document


def get_document_out(db: Session, owner: User, document_id: uuid.UUID) -> DocumentOut:
    document = get_document(db, owner, document_id)
    return to_out(document, documents_repo.chunk_counts(db, [document.id]).get(document.id, 0))


def delete_document(db: Session, storage: Storage, owner: User, document_id: uuid.UUID) -> None:
    document = get_document(db, owner, document_id)
    key = document.storage_key
    db.delete(document)  # chunks and jobs go with it (ON DELETE CASCADE)
    db.commit()
    # After the commit: if deleting the file fails, the document is still gone for the user.
    try:
        storage.delete(key)
    except OSError:
        logger.exception("could not delete stored file", extra={"storage_key": key})


def retry_document(db: Session, owner: User, document_id: uuid.UUID) -> DocumentOut:
    document = get_document(db, owner, document_id)
    if document.status != DocumentStatus.FAILED:
        raise AppError(409, "not_retryable", "Only documents that failed can be retried.")
    document.status = DocumentStatus.UPLOADED
    document.error_code = None
    documents_repo.enqueue_job(db, document.id)
    db.commit()
    db.refresh(document)
    return to_out(document, chunk_count=0)
