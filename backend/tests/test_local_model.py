"""End-to-end check with the real multilingual model (downloads ~220 MB on first run).

Skipped by default. Run with:  RUN_MODEL_TESTS=1 uv run pytest tests/test_local_model.py
For the full measurement (Recall@k, MRR, refusals) run:  uv run python -m eval.run_eval
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services import processing, search_service
from app.services.embeddings import LocalEmbeddingProvider
from tests.conftest import upload

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_MODEL_TESTS") != "1", reason="set RUN_MODEL_TESTS=1 to run"
)


@pytest.fixture(scope="module")
def local_provider() -> LocalEmbeddingProvider:
    return LocalEmbeddingProvider(get_settings().embedding_model, batch_size=16)


@pytest.mark.parametrize(
    ("question", "expected_page"),
    [
        ("وش شروط التسجيل في التدريب التعاوني؟", 2),
        # Dialect question that vector search alone ranked 4th; keyword matching rescues it.
        ("كم نسبة الغياب اللي تحرمني من الاختبار؟", 3),
        ("متى آخر موعد للاعتذار عن الفصل؟", 3),
        ("كم رسوم السكن؟", 4),  # Arabic question, English page
        ("What is the minimum score for admission?", 1),  # English question, Arabic page
    ],
)
def test_real_model_hybrid_search_finds_the_right_page(
    logged_in: TestClient, sample_pdf, local_provider, monkeypatch, question, expected_page
):
    monkeypatch.setattr(processing, "get_embedding_provider", lambda: local_provider)
    upload(logged_in, sample_pdf)
    processing.process_next_job()
    user_id = logged_in.get("/api/v1/auth/me").json()["id"]

    with SessionLocal() as db:
        hits = search_service.search(db, local_provider, user_id, question, limit=1)

    assert hits[0].page_number == expected_page
