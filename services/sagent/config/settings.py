"""Centralised application settings.

All environment variables are read here and exposed as typed attributes.
Every module should import from here instead of calling os.getenv directly.

Usage:
    from config.settings import settings

    db_url = settings.DATABASE_URL
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load .env before reading any env vars.
# Search order (first found wins):
#   1. <project_root>/.env          — preferred: root alongside docker-compose.yml
#   2. <sagent>/.env                — legacy location (backwards compat)
#   3. <sagent>/.env.development    — legacy fallback
#
# File is now at: services/sagent/config/settings.py
# config/ → sagent/ → services/ → project_root
_sagent_dir = Path(__file__).resolve().parent.parent          # services/sagent/
_project_root = _sagent_dir.parent.parent                     # project root

_env_path = (
    _project_root / ".env"
    if (_project_root / ".env").exists()
    else _sagent_dir / ".env"
    if (_sagent_dir / ".env").exists()
    else _sagent_dir / ".env.development"
)
load_dotenv(_env_path, override=False)


def _env(key: str, default: str | None = None, *, required: bool = False) -> str:
    """Read an environment variable with optional default."""
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(
            f"{key} environment variable is required. "
            "Check your .env file or environment configuration."
        )
    return value or ""


@dataclass(frozen=True)
class Settings:
    """Immutable application settings, read once from environment."""

    # ── GCP / Vertex AI ────────────────────────────────────────────
    GOOGLE_CLOUD_PROJECT: str = field(
        default_factory=lambda: _env("GOOGLE_CLOUD_PROJECT", required=True)
    )
    GOOGLE_CLOUD_LOCATION: str = field(
        default_factory=lambda: _env("GOOGLE_CLOUD_LOCATION", "global")
    )
    GOOGLE_GENAI_USE_VERTEXAI: bool = field(
        default_factory=lambda: _env("GOOGLE_GENAI_USE_VERTEXAI", "TRUE").upper() == "TRUE"
    )

    # ── Application ───────────────────────────────────────────────────
    ENVIRONMENT: str = field(default_factory=lambda: _env("ENVIRONMENT", "development"))
    PORT: int = field(default_factory=lambda: int(_env("PORT", "8000")))
    CORS_ORIGINS: str = field(default_factory=lambda: _env("CORS_ORIGINS", ""))

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = field(
        default_factory=lambda: _env("DATABASE_URL", required=True)
    )

    # ── RabbitMQ ────────────────────────────────────────────────────────
    RABBITMQ_URL: str = field(
        default_factory=lambda: _env("RABBITMQ_URL", "amqp://agent:localdev@rabbitmq:5672/")
    )
    QUEUE_RAG_REQUESTS: str = field(default_factory=lambda: _env("QUEUE_RAG_REQUESTS", "rag_requests"))
    QUEUE_INDEXING: str = field(default_factory=lambda: _env("QUEUE_INDEXING", "indexing_tasks"))
    RAG_RPC_TIMEOUT: int = field(default_factory=lambda: int(_env("RAG_RPC_TIMEOUT", "30")))

    # ── RAG Settings ──────────────────────────────────────────────────
    RAG_SIMILARITY_TOP_K: int = field(default_factory=lambda: int(_env("RAG_SIMILARITY_TOP_K", "10")))
    RAG_CHUNK_SIZE: int = field(default_factory=lambda: int(_env("RAG_CHUNK_SIZE", "512")))
    RAG_CHUNK_OVERLAP: int = field(default_factory=lambda: int(_env("RAG_CHUNK_OVERLAP", "100")))

    # ── Team Membership ───────────────────────────────────────────────
    TEAM_MEMBERSHIP_PROVIDER: str = field(
        default_factory=lambda: _env("TEAM_MEMBERSHIP_PROVIDER", "database")
    )

    # ── Artifact Storage ────────────────────────────────────────────
    ARTIFACT_BUCKET: str = field(
        default_factory=lambda: _env("ARTIFACT_BUCKET", "")
    )

    # ── MinIO (S3-compatible object storage — dev only) ───────────
    MINIO_ENDPOINT: str = field(
        default_factory=lambda: _env("MINIO_ENDPOINT", "minio:9000")
    )
    MINIO_ACCESS_KEY: str = field(
        default_factory=lambda: _env("MINIO_ACCESS_KEY", "minioadmin")
    )
    MINIO_SECRET_KEY: str = field(
        default_factory=lambda: _env("MINIO_SECRET_KEY", "minioadmin")
    )
    MINIO_BUCKET: str = field(
        default_factory=lambda: _env("MINIO_BUCKET", "agent-artifacts")
    )
    MINIO_SECURE: bool = field(
        default_factory=lambda: _env("MINIO_SECURE", "false").lower() == "true"
    )
    # Public URL for clients to download artifacts (via nginx proxy)
    MINIO_PUBLIC_URL: str = field(
        default_factory=lambda: _env("MINIO_PUBLIC_URL", "http://localhost:8081/storage")
    )

    # ── Logging ───────────────────────────────────────────────────────
    LOG_LEVEL: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    ADK_LOG_LEVEL: str = field(default_factory=lambda: _env("ADK_LOG_LEVEL", ""))

    # ── Model Config ──────────────────────────────────────────────────
    MODEL_ROOT: str = field(
        default_factory=lambda: _env("MODEL_ROOT", "gemini-2.5-pro")
    )
    MODEL_SEARCH: str = field(
        default_factory=lambda: _env("MODEL_SEARCH", "gemini-2.5-flash")
    )
    MODEL_RAG: str = field(
        default_factory=lambda: _env("MODEL_RAG", "gemini-2.5-flash")
    )
    MODEL_DATA_ANALYST: str = field(
        default_factory=lambda: _env("MODEL_DATA_ANALYST", "gemini-2.5-pro")
    )
    MODEL_TITLE: str = field(
        default_factory=lambda: _env("MODEL_TITLE", "gemini-2.5-flash")
    )
    MODEL_GITLAB: str = field(
        default_factory=lambda: _env("MODEL_GITLAB", "gemini-2.5-flash")
    )
    MODEL_REDMINE: str = field(
        default_factory=lambda: _env("MODEL_REDMINE", "gemini-2.5-flash")
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        if self.CORS_ORIGINS:
            return [o.strip() for o in self.CORS_ORIGINS.split(",")]
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
    """Create and cache settings singleton."""
    return Settings()


# Module-level singleton — import this everywhere
settings: Settings = _get_settings()

