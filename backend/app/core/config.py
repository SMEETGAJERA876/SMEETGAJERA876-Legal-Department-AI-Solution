from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ClauseLens AI"
    environment: str = "development"

    database_url: str = "postgresql+psycopg://clauselens:clauselens@localhost:5433/clauselens"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, url: str) -> str:
        """Accept the plain URLs hosting providers give (postgres://, postgresql://)."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Google sign-in via Firebase Authentication (app/core/auth.py). "disabled" runs everything
    # as one local user and must only be used for local development.
    auth_mode: Literal["firebase", "disabled"] = "firebase"
    firebase_project_id: str = ""

    # Public read-only demo (docs/Demo.md). Documents seeded by `scripts.seed_demo` may be
    # opened, searched and asked about without signing in; uploading, changing the document
    # type, auto-repair and deletion always need Google. Set false to close the demo entirely.
    demo_mode_enabled: bool = True
    # Load the demo documents in the background at start-up, for hosts with no shell to run
    # `scripts.seed_demo` and hosts that lose their uploads directory on restart.
    demo_auto_seed: bool = False

    # HTTP hardening (app/core/security.py).
    rate_limit_enabled: bool = True
    # Behind a reverse proxy/load balancer, rate-limit by X-Forwarded-For instead of the peer.
    trust_proxy_headers: bool = False

    # Document processing (services/jobs.py): "queue" = worker threads claim uploads from the
    # database (safe across processes and machines); "inline" = right after the upload response.
    processing_mode: Literal["queue", "inline"] = "queue"
    processing_workers: int = 2

    # Delete documents automatically this many days after upload (0 = never; users delete).
    retention_days: int = 0
    retention_check_hours: int = 6

    upload_dir: str = "storage/uploads"
    # data/taxonomy (document types, legal concepts). Empty = the repository's data/taxonomy.
    taxonomy_dir: str = ""
    # data/formats (official formats each document kind is compared against). Empty = the
    # repository's data/formats.
    formats_dir: str = ""

    # What to do when there is strong, checkable evidence that a document is not what it
    # claims to be (services/authenticity.py): "warn" accepts it and says so prominently,
    # "reject" refuses it, "off" does not look. Never decided from writing style.
    authenticity_policy: Literal["warn", "reject", "off"] = "warn"
    max_upload_size_mb: int = 25

    # Embeddings run locally (no API key needed); the model is downloaded once.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_cache_dir: str = "storage/models"
    # AES-256-GCM key for uploaded files at rest (app/services/storage.py). Generate one with
    # `uv run python -m scripts.new_encryption_key`. Required when ENVIRONMENT=production.
    file_encryption_key: str = ""
    # Second-stage cross-encoder re-ranker (app/services/reranker.py); "none" turns it off.
    rerank_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"

    # Chat provider for plain-language answers. "none" = answers quote the document
    # directly (no generated text). "anthropic" = Claude writes plain-language explanations.
    ai_provider: Literal["none", "anthropic"] = "none"
    ai_api_key: str = ""
    ai_chat_model: str = "claude-opus-5"
    ai_effort: Literal["low", "medium", "high"] = "medium"


@lru_cache
def get_settings() -> Settings:
    return Settings()
