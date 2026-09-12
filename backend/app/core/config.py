"""Application configuration loaded from environment variables.

All secrets and provider settings must come from the environment.
See the repository root ``.env.example`` for documented variables.
"""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Backend settings. Safe defaults for local development only."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Bizz AI API"
    environment: str = Field(default="development")
    api_v1_prefix: str = "/api/v1"

    # PostgreSQL connection string. Overridden by DATABASE_URL in the environment.
    database_url: str = Field(default="postgresql+psycopg://bizzai:bizzai@localhost:5432/bizzai")

    # Required in real deployments; a dev-only placeholder keeps local setup runnable.
    # JWT signing key — MUST be a long random value outside development.
    secret_key: str = Field(default="dev-only-secret-key-change-me")

    # Authentication token/session handling (Architecture.md §8).
    auth_cookie_name: str = "bizzai_token"
    access_token_expire_minutes: int = Field(default=60 * 24 * 7)

    backend_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ]
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        """Accept JSON lists and comma-separated strings.

        Allows BACKEND_CORS_ORIGINS to be set in `.env` as either:
          BACKEND_CORS_ORIGINS='["http://localhost:3000","http://localhost:3001"]'
        or:
          BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:3001
        """
        import json

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return [
                        str(origin).strip().rstrip("/") for origin in parsed if str(origin).strip()
                    ]
                return value
            return [origin.strip().rstrip("/") for origin in text.split(",") if origin.strip()]
        if isinstance(value, list):
            return [str(origin).strip().rstrip("/") for origin in value if str(origin).strip()]
        return value

    # LLM interpretation layer (Architecture.md §16-19). Disabled by default:
    # core analytics/ML work without any provider configured.
    llm_provider: str = Field(default="disabled")
    gemini_api_key: str | None = Field(default=None)
    gemini_model: str = Field(default="gemini-3.6-flash")
    groq_api_key: str | None = Field(default=None)
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    llm_timeout_seconds: float = Field(default=30.0, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
