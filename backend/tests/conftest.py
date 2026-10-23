"""Test setup: a real PostgreSQL test database, migrated with Alembic, cleaned between tests.

Tests run against real Postgres (not SQLite) so they exercise the same SQL, constraints
and extensions as production.
"""

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/daleel_test"
)
os.environ.setdefault("JWT_SECRET", "test-secret-value-for-pytest-only")

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    """Build the schema from migrations once, so the migrations themselves are tested too."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    yield
    table_names = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def register_user(
    client: TestClient, email: str = "jana@example.com", password: str = "s3cure-pass"
):
    return client.post(
        "/api/v1/auth/register",
        json={"name": "Jana", "email": email, "password": password},
    )
