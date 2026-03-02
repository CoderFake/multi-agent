"""
Memory Service — Mem0 wrapper for long-term memory
Provides async interface over mem0's sync SDK.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any

from core.config import settings

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Singleton wrapper around mem0 Memory.
    Uses OpenAI for fact extraction and embeddings.
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

    def _get_memory(self):
        """Lazy-init mem0 Memory (heavy import, do it on first use)."""
        if self._memory is None:
            try:
                from mem0 import Memory

                config = {
                    "llm": {
                        "provider": "openai",
                        "config": {
                            "model": "gpt-4.1-nano",
                            "temperature": 0.1,
                            "api_key": settings.openai_api_key,
                        },
                    },
                    "embedder": {
                        "provider": "openai",
                        "config": {
                            "model": "text-embedding-3-small",
                            "api_key": settings.openai_api_key,
                        },
                    },
                    "vector_store": {
                        "provider": "qdrant",
                        "config": {
                            "collection_name": "agent_memories",
                            "path": "/tmp/qdrant_mem0",
                        },
                    },
                }

                self._memory = Memory.from_config(config)
                logger.info("Mem0 memory service initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize Mem0: %s", e)
                raise
        return self._memory

    async def add_memory(
        self,
        messages: List[Dict[str, str]],
        user_id: str = "default_user",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Store conversation messages in mem0.
        Runs in thread pool to avoid blocking.
        """
        try:
            memory = self._get_memory()
            kwargs = {"user_id": user_id}
            if metadata:
                kwargs["metadata"] = metadata

            result = await asyncio.to_thread(memory.add, messages, **kwargs)
            logger.info("Memory added for user '%s': %s", user_id, result)
            return result
        except Exception as e:
            logger.error("Error adding memory for user '%s': %s", user_id, e)
            return {"error": str(e)}

    async def search_memories(
        self,
        query: str,
        user_id: str = "default_user",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search relevant memories for a query.
        Returns list of memory dicts with 'memory' and 'score' keys.
        """
        try:
            memory = self._get_memory()
            result = await asyncio.to_thread(
                memory.search, query, user_id=user_id, limit=limit
            )
            memories = result.get("results", []) if isinstance(result, dict) else result
            logger.info(
                "Found %d memories for user '%s' (query: '%s')",
                len(memories), user_id, query[:50],
            )
            return memories
        except Exception as e:
            logger.error("Error searching memories: %s", e)
            return []

    async def get_all_memories(
        self, user_id: str = "default_user"
    ) -> List[Dict[str, Any]]:
        """Get all stored memories for a user."""
        try:
            memory = self._get_memory()
            result = await asyncio.to_thread(memory.get_all, user_id=user_id)
            memories = result.get("results", []) if isinstance(result, dict) else result
            return memories
        except Exception as e:
            logger.error("Error getting all memories: %s", e)
            return []

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory by ID."""
        try:
            memory = self._get_memory()
            await asyncio.to_thread(memory.delete, memory_id)
            logger.info("Deleted memory: %s", memory_id)
            return True
        except Exception as e:
            logger.error("Error deleting memory '%s': %s", memory_id, e)
            return False

    async def delete_all_memories(self, user_id: str = "default_user") -> bool:
        """Delete all memories for a user."""
        try:
            memory = self._get_memory()
            await asyncio.to_thread(memory.delete_all, user_id=user_id)
            logger.info("Deleted all memories for user '%s'", user_id)
            return True
        except Exception as e:
            logger.error("Error deleting all memories for user '%s': %s", user_id, e)
            return False


# Global singleton
memory_service = MemoryService()
