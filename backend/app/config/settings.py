"""
Application settings loaded from environment variables.
Uses pydantic-settings for validation and type coercion.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.common.enums import Environment


class Settings(BaseSettings):
    """CMS Backend configuration."""

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "CMS Backend"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Environment.DEVELOPMENT.value
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    CMS_PORT: int = 8002
    TIMEZONE: str = "Asia/Ho_Chi_Minh"

    # ── Database ─────────────────────────────────────────────────────────
    CMS_DATABASE_URL: str = "postgresql+asyncpg://agent:localdev@localhost:5433/cms"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # ── Redis ────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6380/0"
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5

    # ── Cache TTL (seconds) ──────────────────────────────────────────────
    CACHE_DEFAULT_TTL: int = 3600       # 1 hour
    CACHE_USER_TTL: int = 3600
    CACHE_PERMISSION_TTL: int = 300     # 5 minutes
    CACHE_ORG_TTL: int = 3600
    CACHE_AGENT_TTL: int = 3600
    CACHE_PROVIDER_TTL: int = 7200      # 2 hours
    CACHE_BLACKLIST_TTL: int = 86400    # 24 hours
    CACHE_AGENT_MCP_TOOLSET_TTL: int = 3600  # 1 hour — runtime MCP toolset
    AUTH_CACHE_TTL: int = 300           # 5 minutes
    
    # ── Invite Settings ──────────────────────────────────────────────────
    INVITE_EXPIRE_HOURS: int = 72       # 3 days
    INVITE_TEMP_PASSWORD_LENGTH: int = 16

    # ── JWT ───────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-this-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Encryption ───────────────────────────────────────────────────────
    ENCRYPTION_KEY: Optional[str] = None  # Fernet key for provider API keys

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # ── MinIO ────────────────────────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9010"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = "cms-documents"
    MINIO_INTERNAL_ENDPOINT: str = "minio:9000"  # Docker internal endpoint
    MINIO_PUBLIC_URL: str = "http://localhost:8081/storage"
    BUCKET_SYSTEM: str = "system"

    # ── Superuser ────────────────────────────────────────────────────────
    SUPERUSER_EMAIL: str = "admin@cmsadmin.com"
    SUPERUSER_PASSWORD: str = "admin123"
    SUPERUSER_FULL_NAME: str = "CMS Admin"

    # ── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── SMTP ─────────────────────────────────────────────────────────────
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@agent.com"
    SMTP_USE_TLS: bool = True

    # ── RabbitMQ ─────────────────────────────────────────────────────────
    RABBITMQ_URL: str = "amqp://agent:localdev@localhost:5673/"

    # ── Frontend ─────────────────────────────────────────────────────────
    # BASE_DOMAIN: empty = local dev (use FRONTEND_URL), set = production (subdomain.BASE_DOMAIN)
    BASE_DOMAIN: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "DEBUG" not in kwargs:
            self.DEBUG = self.ENVIRONMENT == Environment.DEVELOPMENT.value


settings = Settings()
