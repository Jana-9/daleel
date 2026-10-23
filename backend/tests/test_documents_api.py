from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.conftest import STORAGE_DIR, make_pdf, register_user, upload


def stored_files() -> list[Path]:
    return [p for p in Path(STORAGE_DIR).rglob("*") if p.is_file()]


def test_upload_requires_login(client: TestClient, sample_pdf):
    assert upload(client, sample_pdf).status_code == 401


def test_upload_stores_file_and_queues_processing(logged_in: TestClient, sample_pdf):
    response = upload(logged_in, sample_pdf, filename="دليل الطالب.pdf")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "uploaded"
    assert body["page_count"] == 4
    assert body["file_size"] == len(sample_pdf)
    assert body["original_filename"] == "دليل الطالب.pdf"
    assert body["title"] == "Daleel sample student guide (fictional)"  # from PDF metadata
    assert body["chunk_count"] == 0
    assert len(stored_files()) == 1


def test_storage_path_never_uses_the_uploaded_filename(logged_in: TestClient, sample_pdf):
    response = upload(logged_in, sample_pdf, filename="../../../etc/passwd.pdf")

    assert response.status_code == 201
    assert response.json()["original_filename"] == "passwd.pdf"
    [stored] = stored_files()
    assert stored.resolve().is_relative_to(Path(STORAGE_DIR).resolve())
    assert "passwd" not in stored.name


def test_upload_rejects_non_pdf_even_with_pdf_name(logged_in: TestClient):
    response = upload(logged_in, b"MZ\x90\x00 an executable", filename="cv.pdf")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "not_pdf"
    assert stored_files() == []


def test_upload_rejects_password_protected_pdf(logged_in: TestClient):
    response = upload(logged_in, make_pdf(["x"], password="1234"))
    assert response.json()["error"]["code"] == "encrypted_pdf"


def test_upload_rejects_files_over_the_size_limit(logged_in: TestClient, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_upload_mb", 1)
    big = make_pdf(["x"]) + b"0" * (1024 * 1024)

    response = upload(logged_in, big)

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"
    assert stored_files() == []


def test_list_and_get_documents(logged_in: TestClient, sample_pdf):
    first = upload(logged_in, sample_pdf, "a.pdf").json()
    second = upload(logged_in, sample_pdf, "b.pdf").json()

    items = logged_in.get("/api/v1/documents").json()["items"]
    assert [d["id"] for d in items] == [second["id"], first["id"]]  # newest first
    assert logged_in.get(f"/api/v1/documents/{first['id']}").json()["original_filename"] == "a.pdf"


def test_download_returns_the_original_pdf(logged_in: TestClient, sample_pdf):
    document = upload(logged_in, sample_pdf, "دليل.pdf").json()

    response = logged_in.get(f"/api/v1/documents/{document['id']}/file")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.content == sample_pdf


def test_users_cannot_see_or_touch_each_others_documents(
    logged_in: TestClient, other_client: TestClient, sample_pdf
):
    document_id = upload(logged_in, sample_pdf).json()["id"]
    register_user(other_client, email="someone-else@example.com")

    assert other_client.get("/api/v1/documents").json()["items"] == []
    for method, path in [
        ("GET", f"/api/v1/documents/{document_id}"),
        ("GET", f"/api/v1/documents/{document_id}/file"),
        ("POST", f"/api/v1/documents/{document_id}/retry"),
        ("DELETE", f"/api/v1/documents/{document_id}"),
    ]:
        response = other_client.request(method, path)
        # 404, not 403: the response does not even confirm that the document exists.
        assert response.status_code == 404, (method, path)
        assert response.json()["error"]["code"] == "document_not_found"

    assert logged_in.get(f"/api/v1/documents/{document_id}").status_code == 200


def test_delete_removes_document_and_file(logged_in: TestClient, sample_pdf):
    document_id = upload(logged_in, sample_pdf).json()["id"]

    assert logged_in.delete(f"/api/v1/documents/{document_id}").status_code == 204
    assert logged_in.get(f"/api/v1/documents/{document_id}").status_code == 404
    assert stored_files() == []


def test_retry_is_only_allowed_for_failed_documents(logged_in: TestClient, sample_pdf):
    document_id = upload(logged_in, sample_pdf).json()["id"]
    response = logged_in.post(f"/api/v1/documents/{document_id}/retry")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_retryable"


def test_invalid_document_id_is_a_validation_error(logged_in: TestClient):
    assert logged_in.get("/api/v1/documents/not-a-uuid").status_code == 422
