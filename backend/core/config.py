from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path

# Get the project root directory (parent of backend)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application configuration"""
    
    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    
    # Frontend
    frontend_url: str = "http://localhost:3000"
    
    # LLM Provider
    provider: str = "openai"  # "openai", "gemini", or "ollama"
    model: str = "gpt-4-turbo-preview"  # Model name for the selected provider
    
    # OpenAI
    openai_api_key: str = ""
    
    # Gemini
    gemini_api_key: str = ""
    
    # Ollama
    ollama_base_url: str = "https://ollama1.nws-dev.com"
    
    # Tavily
    tavily_api_key: str = ""
    
    # LangSmith (optional)
    langsmith_api_key: str = ""
    langsmith_tracing: bool = False
    
    # MCP
    mcp_storage_path: str = "./mcp_data"
    
    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file


settings = Settings()
