import pytest
from pydantic import ValidationError

from app.core.config import DEV_JWT_SECRET, Settings


def test_production_rejects_development_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(environment="production", jwt_secret=DEV_JWT_SECRET, cookie_secure=True)


def test_production_requires_secure_cookie():
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings(environment="production", jwt_secret="x" * 40, cookie_secure=False)


def test_production_rejects_fake_embeddings():
    with pytest.raises(ValidationError, match="EMBEDDING_PROVIDER"):
        Settings(
            environment="production",
            jwt_secret="x" * 40,
            cookie_secure=True,
            embedding_provider="fake",
        )


def test_production_accepts_safe_settings():
    settings = Settings(
        environment="production",
        jwt_secret="x" * 40,
        cookie_secure=True,
        embedding_provider="local",
    )
    assert settings.is_production


def test_chunk_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValidationError, match="CHUNK_OVERLAP"):
        Settings(chunk_size=300, chunk_overlap=300)
