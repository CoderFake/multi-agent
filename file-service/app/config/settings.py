# file-service settings
from pydantic_settings import BaseSettings
from pathlib import Path

FILE_SERVICE_DIR = Path(__file__).parent.parent.parent
ROOT_DIR = FILE_SERVICE_DIR.parent   # agent/
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    """File-service configuration."""

    # gRPC
    grpc_host: str = "0.0.0.0"
    grpc_port: int = 50051

    # FastAPI (health / debug endpoints)
    api_host: str = "0.0.0.0"
    api_port: int = 8001

    # PostgreSQL (shared with backend) — maps to POSTGRES_* in root .env
    postgres_host: str = "localhost"
    postgres_port: int = 25432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "pageindex_db"

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
    model: str = "gpt-5-nano"

    # OpenAI
    openai_api_key: str = ""

    # Gemini
    gemini_api_key: str = ""

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19535
    milvus_collection: str = "agent_knowledge"
    milvus_embedding_dim: int = 1536       # text-embedding-3-small; change if using Gemini/Ollama
    milvus_nlist: int = 128                # IVF_FLAT index nlist
    milvus_nprobe: int = 10               # search nprobe
    knowledge_top_k: int = 8              # default top-K for KnowledgeSearch

    # Hybrid extractor
    min_block_density: float = 3.0        # blocks/page below which a PDF is treated as scanned

    # Temp directory for processing
    temp_dir: str = "/tmp/file-service"

    model_config = {"env_file": str(ENV_FILE), "case_sensitive": False, "extra": "ignore"}


settings = Settings()
