"""End-to-end check with the real multilingual model (downloads ~220 MB on first run).

Skipped by default. Run with:  RUN_MODEL_TESTS=1 uv run pytest tests/test_local_model.py
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.document import DocumentChunk
from app.services import embeddings, processing
from tests.conftest import upload

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_MODEL_TESTS") != "1", reason="set RUN_MODEL_TESTS=1 to run"
)


@pytest.fixture(scope="module")
def local_provider() -> embeddings.LocalEmbeddingProvider:
    settings = get_settings()
    return embeddings.LocalEmbeddingProvider(settings.embedding_model, batch_size=16)


def nearest_page(query_vector: list[float]) -> int:
    with SessionLocal() as db:
        return db.scalar(
            select(DocumentChunk.page_number)
            .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(1)
        )


@pytest.mark.parametrize(
    ("question", "expected_page"),
    [
        ("وش شروط التسجيل في التدريب التعاوني؟", 2),
        pytest.param(
            "كم نسبة الغياب اللي تحرمني من الاختبار؟",
            3,
            # Known gap: dialect wording defeats this small model with vector search alone.
            # Phase 3 adds keyword matching (hybrid search); strict=True makes this test fail
            # loudly once the case starts passing, so the marker gets removed.
            marks=pytest.mark.xfail(strict=True, reason="needs hybrid search (Phase 3)"),
        ),
        ("متى آخر موعد للاعتذار عن الفصل؟", 3),
        ("كم رسوم السكن؟", 4),  # Arabic question, English page
        ("What is the minimum score for admission?", 1),  # English question, Arabic page
    ],
)
def test_real_model_finds_the_right_page(
    logged_in: TestClient, sample_pdf, local_provider, monkeypatch, question, expected_page
):
    monkeypatch.setattr(processing, "get_embedding_provider", lambda: local_provider)
    upload(logged_in, sample_pdf)
    processing.process_next_job()

    assert nearest_page(local_provider.embed_query(question)) == expected_page
