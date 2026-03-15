"""Centralised configuration for the retrieval microservice.

All environment variables are read here. Every module should import
from here instead of calling os.getenv directly.

Usage:
    from app.config.settings import settings
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
_root_env = _project_root / ".env"
if _root_env.exists():
    load_dotenv(_root_env, override=False)


def _env(key: str, default: str | None = None) -> str:
    """Read an environment variable with optional default."""
    return os.getenv(key, default) or ""


@dataclass(frozen=True)
class Settings:
    """Immutable retrieval service settings, read once from environment."""

    # ── Milvus ────────────────────────────────────────────────────────
    MILVUS_HOST: str = field(default_factory=lambda: _env("MILVUS_HOST", "milvus"))
    MILVUS_PORT: int = field(default_factory=lambda: int(_env("MILVUS_PORT", "19530")))

    # ── Redis ─────────────────────────────────────────────────────────
    REDIS_URL: str = field(default_factory=lambda: _env("REDIS_URL", "redis://localhost:6380/0"))
    TASK_TTL: int = field(default_factory=lambda: int(_env("TASK_TTL", "86400")))  # 24h
    LOCK_TTL: int = field(default_factory=lambda: int(_env("LOCK_TTL", "3600")))   # 1h

    # ── RabbitMQ ──────────────────────────────────────────────────────
    RABBITMQ_URL: str = field(
        default_factory=lambda: _env("RABBITMQ_URL", "amqp://agent:localdev@rabbitmq:5672/")
    )

    # ── Queue Names ───────────────────────────────────────────────────
    QUEUE_INDEXING: str = field(default_factory=lambda: _env("QUEUE_INDEXING", "indexing_tasks"))
    QUEUE_RAG_REQUESTS: str = field(default_factory=lambda: _env("QUEUE_RAG_REQUESTS", "rag_requests"))

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = field(
        default_factory=lambda: _env("DATABASE_URL", "postgresql://agent:localdev@postgres:5432/agent")
    )

    # ── Embedding ─────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = field(default_factory=lambda: _env("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    EMBEDDING_DIMENSION: int = field(default_factory=lambda: int(_env("EMBEDDING_DIMENSION", "384")))

    # ── Search ────────────────────────────────────────────────────────
    DEFAULT_TOP_K: int = field(default_factory=lambda: int(_env("DEFAULT_TOP_K", "10")))

    # ── MinIO ─────────────────────────────────────────────────────────
    MINIO_ENDPOINT: str = field(default_factory=lambda: _env("MINIO_ENDPOINT", "localhost:9000"))
    MINIO_ACCESS_KEY: str = field(default_factory=lambda: _env("MINIO_ACCESS_KEY", "minioadmin"))
    MINIO_SECRET_KEY: str = field(default_factory=lambda: _env("MINIO_SECRET_KEY", "minioadmin"))
    MINIO_BUCKET: str = field(default_factory=lambda: _env("MINIO_BUCKET", "nws"))
    MINIO_SECURE: bool = field(default_factory=lambda: _env("MINIO_SECURE", "false").lower() == "true")

    # ── Chunking ──────────────────────────────────────────────────────
    CHUNK_SIZE: int = field(default_factory=lambda: int(_env("CHUNK_SIZE", "512")))
    CHUNK_OVERLAP: int = field(default_factory=lambda: int(_env("CHUNK_OVERLAP", "50")))

    # ── Extraction ────────────────────────────────────────────────────
    OCR_DEVICE: str = field(default_factory=lambda: _env("OCR_DEVICE", "cpu"))
    MIN_BLOCK_DENSITY: float = field(default_factory=lambda: float(_env("MIN_BLOCK_DENSITY", "3.0")))
    TEMP_DIR: str = field(default_factory=lambda: _env("TEMP_DIR", "/tmp/retrieval"))

    # ── Milvus Index ──────────────────────────────────────────────────
    MILVUS_NLIST: int = field(default_factory=lambda: int(_env("MILVUS_NLIST", "128")))
    MILVUS_NPROBE: int = field(default_factory=lambda: int(_env("MILVUS_NPROBE", "10")))

    @property
    def milvus_uri(self) -> str:
        """Full Milvus connection URI."""
        return f"http://{self.MILVUS_HOST}:{self.MILVUS_PORT}"


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
    return Settings()


settings: Settings = _get_settings()
