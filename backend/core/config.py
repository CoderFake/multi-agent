from pydantic_settings import BaseSettings
from pathlib import Path

# Root .env — shared by backend, file-service, and docker-compose
ROOT_DIR = Path(__file__).parent.parent.parent   # agent/
ENV_FILE = ROOT_DIR / ".env"
BACKEND_DIR = Path(__file__).parent.parent

# Prompt YAMLs directory
PROMPTS_DIR = BACKEND_DIR / "static" / "prompts"


class Settings(BaseSettings):
    """Application configuration"""

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # LLM Provider
    provider: str = "openai"   # "openai" | "gemini" | "ollama"
    model: str = "gpt-4o"

    # OpenAI
    openai_api_key: str = ""

    # Gemini
    gemini_api_key: str = ""

    # Ollama
    ollama_base_url: str = "https://ollama1.nws-dev.com"

    # File-service gRPC
    file_service_grpc_url: str = "localhost:50051"
    knowledge_top_k: int = 8

    # Tavily
    tavily_api_key: str = ""

    # LangSmith (optional tracing)
    langsmith_api_key: str = ""
    langsmith_tracing: bool = False

    # MCP
    mcp_storage_path: str = "./mcp_data"

    # ── PostgreSQL (shared DB) ─────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 25432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "pageindex_db"

    # ── Mem0 ────────────────────────────────────────────
    mem0_enabled: bool = True
    mem0_collection: str = "agent_memories"
    mem0_embedder_model: str = "text-embedding-3-small"
    mem0_embedder_dims: int = 1536

    # Mem0 PostgreSQL — reuse POSTGRES_* (no duplicate needed)
    @property
    def mem0_pg_host(self) -> str: return self.postgres_host
    @property
    def mem0_pg_port(self) -> int: return self.postgres_port
    @property
    def mem0_pg_user(self) -> str: return self.postgres_user
    @property
    def mem0_pg_password(self) -> str: return self.postgres_password
    @property
    def mem0_pg_db(self) -> str: return self.postgres_db

    # ── Firebase Admin SDK ────────────────────────────
    firebase_type: str = "service_account"
    firebase_project_id: str = ""
    firebase_private_key_id: str = ""
    firebase_private_key: str = ""
    firebase_client_email: str = ""
    firebase_client_id: str = ""
    firebase_auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    firebase_token_uri: str = "https://oauth2.googleapis.com/token"

    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = False
        extra = "ignore"


settings = Settings()
