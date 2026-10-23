import uuid

from fastapi.testclient import TestClient
from sqlalchemy import update

from app.db.session import SessionLocal
from app.models.document import DocumentChunk
from app.services import processing
from app.services.search_service import keyword_terms
from tests.conftest import register_user, upload


def test_keyword_terms_drop_question_words_and_article():
    assert keyword_terms("كم نسبة الغياب اللي تحرمني من الاختبار؟") == [
        "نسبه",
        "غياب",
        "تحرمني",
        "اختبار",
    ]


def test_keyword_terms_handle_english_and_numbers():
    assert keyword_terms("How much does a parking permit cost in 2026?") == [
        "parking",
        "permit",
        "cost",
        "2026",
    ]


def test_keyword_terms_are_distinct_and_strip_combined_prefixes():
    assert keyword_terms("والتدريب بالتدريب التدريب") == ["تدريب"]


def search(client: TestClient, query: str, **extra):
    return client.post("/api/v1/search", json={"query": query, **extra})


def test_search_finds_the_passage_with_page_and_excerpt(logged_in: TestClient, ready_document):
    response = search(logged_in, "نسبة الغياب التي تحرم من الاختبار النهائي")

    assert response.status_code == 200
    top = response.json()["items"][0]
    assert top["page_number"] == 3
    assert "25 بالمئة" in top["excerpt"]
    assert top["keyword_matched"] is True
    assert top["document_id"] == ready_document["id"]


def test_search_only_covers_the_users_own_documents(
    logged_in: TestClient, other_client: TestClient, ready_document
):
    register_user(other_client, email="other@example.com")
    assert search(other_client, "التدريب التعاوني").json()["items"] == []


def test_search_ignores_documents_that_are_not_ready(logged_in: TestClient, sample_pdf):
    upload(logged_in, sample_pdf)  # queued, not processed
    assert search(logged_in, "التدريب التعاوني").json()["items"] == []


def test_search_can_be_limited_to_one_document(logged_in: TestClient, ready_document, sample_pdf):
    other = upload(logged_in, sample_pdf, "copy.pdf").json()
    processing.process_next_job()

    items = search(logged_in, "التدريب التعاوني", document_id=other["id"]).json()["items"]

    assert items
    assert {i["document_id"] for i in items} == {other["id"]}


def test_search_ignores_vectors_from_another_embedding_model(logged_in: TestClient, ready_document):
    # After switching models, old vectors are not comparable and must not be mixed in.
    with SessionLocal() as db, db.begin():
        db.execute(update(DocumentChunk).values(embedding_model="some-older-model"))
    assert search(logged_in, "التدريب التعاوني").json()["items"] == []


def test_search_requires_login(client: TestClient):
    assert search(client, "anything").status_code == 401


def test_search_validates_input(logged_in: TestClient):
    assert search(logged_in, "x").status_code == 422
    assert search(logged_in, "valid", limit=50).status_code == 422
    assert search(logged_in, "valid", document_id=str(uuid.uuid4())).json()["items"] == []
