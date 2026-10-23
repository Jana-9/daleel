"""Test setup: a real PostgreSQL test database, migrated with Alembic, cleaned between tests.

Tests run against real Postgres (not SQLite) so they exercise the same SQL, constraints
and extensions (pgvector) as production. They never download or call an AI model: the
embedding provider is the deterministic fake.
"""

import os
import tempfile

STORAGE_DIR = tempfile.mkdtemp(prefix="daleel-test-storage-")

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/daleel_test"
)
os.environ.setdefault("JWT_SECRET", "test-secret-value-for-pytest-only")
os.environ["STORAGE_DIR"] = STORAGE_DIR
os.environ["EMBEDDING_PROVIDER"] = "fake"
os.environ["RUN_WORKER_IN_API"] = "false"  # tests drive the worker step by step

import shutil  # noqa: E402
from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pymupdf  # noqa: E402
import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
SAMPLE_PDF = BACKEND_DIR.parent / "samples" / "daleel-sample-guide.pdf"


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    """Build the schema from migrations once, so the migrations themselves are tested too."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield
    shutil.rmtree(STORAGE_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    yield
    table_names = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
    for child in Path(STORAGE_DIR).iterdir():
        shutil.rmtree(child, ignore_errors=True)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def other_client() -> Iterator[TestClient]:
    """A second, independent browser session (for testing that users cannot see each other)."""
    with TestClient(app) as test_client:
        yield test_client


def register_user(
    client: TestClient, email: str = "jana@example.com", password: str = "s3cure-pass"
):
    return client.post(
        "/api/v1/auth/register",
        json={"name": "Jana", "email": email, "password": password},
    )


@pytest.fixture
def logged_in(client: TestClient) -> TestClient:
    assert register_user(client).status_code == 201
    return client


@pytest.fixture
def sample_pdf() -> bytes:
    return SAMPLE_PDF.read_bytes()


def make_pdf(pages: list[str] | None = None, *, blank_pages: int = 0, password: str = "") -> bytes:
    """Build a small PDF in memory. `blank_pages` have only a drawn shape, like a scan."""
    doc = pymupdf.open()
    for content in pages or []:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(50, 50, 550, 800), content, fontsize=11)
    for _ in range(blank_pages):
        page = doc.new_page()
        page.draw_rect(pymupdf.Rect(100, 100, 400, 400), color=(0, 0, 0), fill=(0.8, 0.8, 0.8))
    if password:
        return doc.tobytes(
            encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password
        )
    return doc.tobytes()


def upload(client: TestClient, data: bytes, filename: str = "guide.pdf"):
    return client.post("/api/v1/documents", files={"file": (filename, data, "application/pdf")})
