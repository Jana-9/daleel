import threading
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.document import Document, DocumentChunk, JobStatus, ProcessingJob
from app.repositories import documents as documents_repo
from app.services import processing
from app.services.embeddings import EmbeddingError, FakeEmbeddingProvider
from tests.conftest import make_pdf, upload


def get(client: TestClient, document_id: str) -> dict:
    return client.get(f"/api/v1/documents/{document_id}").json()


def chunks_of(document_id: str) -> list[DocumentChunk]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == uuid.UUID(document_id))
                .order_by(DocumentChunk.chunk_index)
            )
        )


def test_worker_processes_a_document_until_ready(logged_in: TestClient, sample_pdf):
    document_id = upload(logged_in, sample_pdf).json()["id"]

    assert processing.process_next_job() is True
    assert processing.process_next_job() is False  # queue is empty

    document = get(logged_in, document_id)
    assert document["status"] == "ready"
    assert document["error_code"] is None
    assert document["processed_at"] is not None
    chunks = chunks_of(document_id)
    assert document["chunk_count"] == len(chunks) >= 4
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert {c.page_number for c in chunks} == {1, 2, 3, 4}


def test_chunks_carry_page_numbers_text_positions_and_vectors(logged_in: TestClient, sample_pdf):
    document_id = upload(logged_in, sample_pdf).json()["id"]
    processing.process_next_job()

    chunks = chunks_of(document_id)
    training = next(c for c in chunks if "ثمانية أسابيع متصلة" in c.content)
    assert training.page_number == 2
    assert "ثمانيه اسابيع متصله" in training.content_normalized
    assert training.bboxes and all(len(rect) == 4 for rect in training.bboxes)
    assert len(training.embedding) == 384
    assert training.embedding_model == FakeEmbeddingProvider.model_name
    assert all(len(c.content) <= get_settings().chunk_size for c in chunks)


def test_scanned_pdf_fails_with_clear_code(logged_in: TestClient):
    document_id = upload(logged_in, make_pdf(blank_pages=3)).json()["id"]

    processing.process_next_job()

    document = get(logged_in, document_id)
    assert document["status"] == "failed"
    assert document["error_code"] == "scanned_pdf"
    assert chunks_of(document_id) == []


def test_transient_errors_are_retried_then_fail(logged_in: TestClient, sample_pdf, monkeypatch):
    def broken(*_args, **_kwargs):
        raise EmbeddingError("model download interrupted")

    monkeypatch.setattr(FakeEmbeddingProvider, "embed_documents", broken)
    document_id = upload(logged_in, sample_pdf).json()["id"]

    for attempt in range(1, get_settings().job_max_attempts):
        processing.process_next_job()
        assert get(logged_in, document_id)["status"] == "uploaded", f"attempt {attempt}"

    processing.process_next_job()  # last allowed attempt
    document = get(logged_in, document_id)
    assert document["status"] == "failed"
    assert document["error_code"] == "embedding_failed"
    assert processing.process_next_job() is False


def test_retry_after_failure_reprocesses_without_duplicate_chunks(
    logged_in: TestClient, sample_pdf
):
    document_id = upload(logged_in, sample_pdf).json()["id"]
    processing.process_next_job()
    first_count = len(chunks_of(document_id))

    # Simulate a failed state (e.g. after a bad deploy) and let the user retry.
    with SessionLocal() as db, db.begin():
        db.execute(update(ProcessingJob).values(status=JobStatus.FAILED))
        db.execute(update(Document).values(status="failed", error_code="internal_error"))

    response = logged_in.post(f"/api/v1/documents/{document_id}/retry")
    assert response.status_code == 200
    assert response.json()["status"] == "uploaded"
    processing.process_next_job()

    assert get(logged_in, document_id)["status"] == "ready"
    assert len(chunks_of(document_id)) == first_count  # replaced, not duplicated


def test_document_deleted_during_processing_is_discarded(
    logged_in: TestClient, sample_pdf, monkeypatch
):
    document_id = upload(logged_in, sample_pdf).json()["id"]
    original = processing._build_chunks

    def delete_midway(document, path):
        chunks = original(document, path)
        assert logged_in.delete(f"/api/v1/documents/{document_id}").status_code == 204
        return chunks

    monkeypatch.setattr(processing, "_build_chunks", delete_midway)
    processing.process_next_job()  # must not crash or resurrect the document

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(DocumentChunk)) == 0


def test_concurrent_workers_never_claim_the_same_job(logged_in: TestClient, sample_pdf):
    for i in range(5):
        upload(logged_in, sample_pdf, f"{i}.pdf")

    claimed: list[uuid.UUID] = []
    lock = threading.Lock()

    def worker():
        while True:
            with SessionLocal() as db, db.begin():
                job_id = documents_repo.claim_next_job(db)
            if job_id is None:
                return
            with lock:
                claimed.append(job_id)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(claimed) == 5
    assert len(set(claimed)) == 5


def test_stale_running_jobs_are_requeued(logged_in: TestClient, sample_pdf):
    upload(logged_in, sample_pdf)
    with SessionLocal() as db, db.begin():
        job_id = documents_repo.claim_next_job(db)
        # Pretend the worker that claimed it crashed an hour ago.
        db.execute(
            update(ProcessingJob)
            .where(ProcessingJob.id == job_id)
            .values(locked_at=datetime.now(UTC) - timedelta(hours=1))
        )

    assert processing.requeue_stale_jobs() == 1
    assert processing.process_next_job() is True
