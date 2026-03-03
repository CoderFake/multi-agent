# file-service settings
from pydantic_settings import BaseSettings
from pathlib import Path

FILE_SERVICE_DIR = Path(__file__).parent.parent.parent
ENV_FILE = FILE_SERVICE_DIR / ".env"


class Settings(BaseSettings):
    """File-service configuration."""

    # gRPC
    grpc_host: str = "0.0.0.0"
    grpc_port: int = 50051

    # FastAPI (health / debug endpoints)
    api_host: str = "0.0.0.0"
    api_port: int = 8001

    # PostgreSQL (shared with backend)
    pg_host: str = "localhost"
    pg_port: int = 25432
    pg_user: str = "postgres"
    pg_password: str = "postgres"
    pg_db: str = "pageindex_db"

    # MinIO — SDK endpoint (internal docker network)
    minio_endpoint: str = "localhost:29000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "documents"
    minio_secure: bool = False

    # MinIO external URL (nginx rewrites internal→external)
    minio_external_url: str = "http://localhost:29000"

    # PaddleOCR
    ocr_device: str = "cpu"  # "cpu" | "gpu"

    # LLM Provider (same pattern as backend)
    provider: str = "openai"   # "openai" | "gemini" | "ollama"
    model: str = "gpt-4o-2024-11-20"

    # OpenAI
    openai_api_key: str = ""

    # Gemini
    gemini_api_key: str = ""

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # Temp directory for processing
    temp_dir: str = "/tmp/file-service"

    model_config = {"env_file": str(ENV_FILE), "case_sensitive": False, "extra": "ignore"}


settings = Settings()
