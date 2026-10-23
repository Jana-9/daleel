"""Central application settings, loaded from environment variables (and .env in development)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "change-me-in-production"

# The vector column size is fixed by a migration, so it lives here as a constant rather than a
# setting. Changing the embedding model to one with another size needs a new migration.
EMBEDDING_DIM = 384


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/daleel"

    # Auth
    jwt_secret: str = Field(default=DEV_JWT_SECRET, min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24
    auth_cookie_name: str = "daleel_session"
    # Must be True in production (HTTPS). False locally so the cookie works on http://localhost.
    cookie_secure: bool = False

    # Uploads
    storage_dir: str = "storage"
    max_upload_mb: int = Field(default=20, ge=1)
    max_pages: int = Field(default=500, ge=1)

    # Text chunking, in characters. The default embedding model reads at most 128 tokens per
    # text (~3.9 Arabic characters per token); 450 characters stays safely under that, so no
    # part of a chunk is silently ignored. Raise these only with a model that reads more.
    chunk_size: int = Field(default=450, ge=200)
    chunk_overlap: int = Field(default=90, ge=0)

    # Embeddings. "local" runs a free multilingual model on this machine (downloaded once);
    # "fake" is a deterministic stand-in used by automated tests.
    embedding_provider: Literal["local", "fake"] = "local"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_batch_size: int = Field(default=32, ge=1)

    # Background processing. In development the worker runs inside the API process so one
    # command starts everything; in production run `python -m app.worker` separately.
    run_worker_in_api: bool = True
    worker_poll_seconds: float = Field(default=2.0, gt=0)
    job_max_attempts: int = Field(default=3, ge=1)
    job_stale_minutes: int = Field(default=10, ge=1)

    # Search: how many passages each method contributes, and the Reciprocal Rank Fusion constant.
    search_candidates: int = Field(default=20, ge=1)
    rrf_k: int = Field(default=60, ge=1)
    # In hybrid search, a keyword result only counts if it contains at least this share of the
    # question's keywords. One shared common word (e.g. "رسوم") is weak evidence and, measured on
    # the eval set, pushed correct cross-lingual passages down.
    keyword_min_coverage: float = Field(default=0.6, ge=0, le=1)

    # Answers. "gemini" calls Google's Gemini API (needs GEMINI_API_KEY in .env, never in code);
    # "fake" is a deterministic stand-in used by automated tests.
    llm_provider: Literal["gemini", "fake"] = "gemini"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    llm_timeout_seconds: float = Field(default=30.0, gt=0)
    answer_passages: int = Field(default=6, ge=1, le=12)
    # Below this cosine similarity, a passage that also shares no keyword with the question is
    # treated as unrelated; if nothing is left, the model is not called. Deliberately low: in
    # the eval set, unanswerable questions scored up to 0.67 and answerable ones as low as 0.32,
    # so similarity cannot tell them apart. The model makes the real "not found" decision.
    min_similarity: float = Field(default=0.25, ge=0, le=1)
    # Protects the free API quota and the server: questions per user.
    questions_per_minute: int = Field(default=6, ge=1)
    questions_per_day: int = Field(default=100, ge=1)

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def check_production_safety(self) -> "Settings":
        """Refuse to start in production with settings that are only safe for development."""
        if self.is_production:
            if self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be set to a random value of 32+ characters.")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production (HTTPS).")
            if self.embedding_provider == "fake":
                raise ValueError("EMBEDDING_PROVIDER=fake is for tests only.")
            if self.llm_provider == "fake":
                raise ValueError("LLM_PROVIDER=fake is for tests only.")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
