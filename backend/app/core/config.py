"""Central application settings, loaded from environment variables (and .env in development)."""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "change-me-in-production"


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
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
