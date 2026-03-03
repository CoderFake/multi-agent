"""
Memory Service — Mem0 with PostgreSQL + pgvector backend.

Strategy:
  - add_memory  → mem0 (extraction + vector) + sync results to memories table
  - get_all     → query memories table directly via SQLAlchemy  (fast, no LLM)
  - search      → mem0 vector search (semantic similarity)
  - delete      → mem0 + memories table (keep in sync)

LLM shares PROVIDER + MODEL with the main agent.
Extraction prompt loaded from static/prompts/memory_extraction.yml.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from core.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from models.memory import Memory
from sqlalchemy import delete, select
from core.config import settings

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Singleton wrapper around mem0 + PostgreSQL memories table.
    """

    _instance: Optional["MemoryService"] = None
    _initialized: bool = False

    def __new__(cls) -> "MemoryService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._memory = None

    # ── Private helpers ────────────────────────────────────────────────

    @staticmethod
    def _load_extraction_prompt() -> Optional[str]:
        """Load mem0 fact-extraction prompt from YAML. Falls back to None (mem0 default)."""
        try:
            from utils.prompt_loader import load_prompt
            return load_prompt("memory_extraction", key="prompt")
        except Exception as e:
            logger.warning("Could not load memory_extraction.yml, using mem0 default: %s", e)
            return None

    @staticmethod
    def _build_llm_config() -> dict:
        """Build mem0 LLM config — shares PROVIDER + MODEL with the main agent."""
        provider = settings.provider.lower()
        if provider == "openai":
            return {"provider": "openai", "config": {
                "model": settings.model, "temperature": 0.1,
                "api_key": settings.openai_api_key,
            }}
        elif provider == "gemini":
            return {"provider": "gemini", "config": {
                "model": settings.model, "temperature": 0.1,
                "api_key": settings.gemini_api_key,
            }}
        elif provider == "ollama":
            return {"provider": "ollama", "config": {
                "model": settings.model or settings.ollama_model,
                "ollama_base_url": settings.ollama_base_url,
                "temperature": 0.1,
            }}
        raise ValueError(f"Unsupported LLM provider for mem0: '{provider}'")

    @staticmethod
    def _build_embedder_config() -> dict:
        """Build mem0 embedder config — provider same as main agent."""
        provider = settings.provider.lower()
        base: dict = {
            "model": settings.mem0_embedder_model,
            "embedding_dims": settings.mem0_embedder_dims,
        }
        if provider == "openai":
            base["api_key"] = settings.openai_api_key
        elif provider == "gemini":
            base["api_key"] = settings.gemini_api_key
        elif provider == "ollama":
            base["ollama_base_url"] = settings.ollama_base_url
        else:
            raise ValueError(f"Unsupported provider: '{provider}'")
        return {"provider": provider, "config": base}

    def _build_config(self) -> dict:
        """Assemble full mem0 config — zero hardcoded values."""
        cfg: Dict[str, Any] = {
            "llm": self._build_llm_config(),
            "embedder": self._build_embedder_config(),
            "vector_store": {
                "provider": "pgvector",
                "config": {
                    "host": settings.mem0_pg_host,
                    "port": str(settings.mem0_pg_port),
                    "user": settings.mem0_pg_user,
                    "password": settings.mem0_pg_password,
                    "dbname": settings.mem0_pg_db,
                    "collection_name": settings.mem0_collection,
                    "embedding_model_dims": settings.mem0_embedder_dims,
                    "diskann": False,
                    "hnsw": True,
                },
            },
            "history_db_path": f"postgresql+psycopg2://{settings.mem0_pg_user}:{settings.mem0_pg_password}@{settings.mem0_pg_host}:{settings.mem0_pg_port}/{settings.mem0_pg_db}",
        }
        extraction_prompt = self._load_extraction_prompt()
        if extraction_prompt:
            cfg["custom_fact_extraction_prompt"] = extraction_prompt
        return cfg

    def _get_memory(self):
        """Lazy-init mem0 Memory (heavy import, first-use only)."""
        if self._memory is None:
            try:
                from mem0 import Memory
                cfg = self._build_config()
                self._memory = Memory.from_config(cfg)
                logger.info(
                    "Mem0 initialized — provider=%s embedder=%s pgvector=%s:%s/%s",
                    settings.provider, settings.mem0_embedder_model,
                    settings.mem0_pg_host, settings.mem0_pg_port, settings.mem0_pg_db,
                )
            except Exception as e:
                logger.error("Failed to initialize Mem0: %s", e)
                raise
        return self._memory

    @staticmethod
    async def _sync_to_db(user_id: str, results: list) -> None:
        """
        Upsert memory facts returned by mem0 into our memories table.
        Runs in background — never blocks the caller.
        """
        if not results:
            return
        try:
            async with AsyncSessionLocal() as db:
                for item in results:
                    mem_id = item.get("id")
                    text = item.get("memory") or item.get("text", "")
                    if not mem_id or not text:
                        continue

                    existing = await db.get(Memory, mem_id)
                    if existing:
                        existing.memory = text
                    else:
                        db.add(Memory(
                            id=mem_id,
                            user_id=user_id,
                            memory=text,
                            categories=",".join(item.get("categories", [])) or None,
                        ))
                await db.commit()
        except Exception as e:
            logger.warning("Failed to sync memories to DB: %s", e)

    # ── Public API ─────────────────────────────────────────────────────

    async def add_memory(
        self,
        messages: List[Dict[str, str]],
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Store messages via mem0 (extraction + vector), then sync to memories table."""
        try:
            memory = self._get_memory()
            kwargs: Dict[str, Any] = {"user_id": user_id}
            if metadata:
                kwargs["metadata"] = metadata
            result = await asyncio.to_thread(memory.add, messages, **kwargs)
            logger.info("Memory stored for user '%s'", user_id)

            added = result.get("results", []) if isinstance(result, dict) else []
            if added:
                asyncio.create_task(self._sync_to_db(user_id, added))

            return result
        except Exception as e:
            logger.error("Error adding memory for user '%s': %s", user_id, e)
            return {"error": str(e)}

    async def search_memories(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Semantic search via mem0 vector store."""
        try:
            memory = self._get_memory()
            result = await asyncio.to_thread(
                memory.search, query, user_id=user_id, limit=limit
            )
            memories = result.get("results", []) if isinstance(result, dict) else result
            logger.info("Found %d memories for user '%s'", len(memories), user_id)
            return memories
        except Exception as e:
            logger.error("Error searching memories: %s", e)
            return []

    async def get_all_memories(self, user_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
        """
        Fetch all memories directly from PostgreSQL memories table.
        Much faster than going through mem0's API (no LLM round-trip).
        """
        try:
            result = await db.execute(
                select(Memory)
                .where(Memory.user_id == user_id)
                .order_by(Memory.created_at.desc())
            )
            rows = result.scalars().all()
            return [row.to_dict() for row in rows]
        except Exception as e:
            logger.error("Error getting memories from DB for user '%s': %s", user_id, e)
            return []

    async def delete_memory(self, memory_id: str, db: AsyncSession) -> bool:
        """Delete from mem0 + memories table."""
        try:
            memory = self._get_memory()
            await asyncio.to_thread(memory.delete, memory_id)

            row = await db.get(Memory, memory_id)
            if row:
                await db.delete(row)

            logger.info("Deleted memory: %s", memory_id)
            return True
        except Exception as e:
            logger.error("Error deleting memory '%s': %s", memory_id, e)
            return False

    async def delete_all_memories(self, user_id: str, db: AsyncSession) -> bool:
        """Delete all memories for a user from mem0 + memories table."""
        try:
            memory = self._get_memory()
            await asyncio.to_thread(memory.delete_all, user_id=user_id)

            await db.execute(
                delete(Memory).where(Memory.user_id == user_id)
            )

            logger.info("Deleted all memories for user '%s'", user_id)
            return True
        except Exception as e:
            logger.error("Error deleting all memories for user '%s': %s", user_id, e)
            return False


# Global singleton
memory_service = MemoryService()
