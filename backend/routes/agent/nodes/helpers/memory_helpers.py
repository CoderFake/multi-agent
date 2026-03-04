"""
Mem0 memory helpers for chat_node.
Handles async search + fire-and-forget storage of conversations.
"""

import asyncio
import logging

from core.config import settings

logger = logging.getLogger(__name__)

_memory_service = None


def _get_memory_service():
    global _memory_service
    if _memory_service is None and settings.mem0_enabled:
        try:
            from services.memory_service import memory_service
            _memory_service = memory_service
        except Exception as e:
            logger.warning("Failed to load memory service: %s", e)
    return _memory_service


async def search_user_memories(user_message: str, user_id: str) -> str:
    """
    Search mem0 for relevant memories (max 3s timeout).
    Returns a formatted string or empty string if no memories / timeout.
    """
    svc = _get_memory_service()
    if not svc:
        return ""

    try:
        memories = await asyncio.wait_for(
            svc.search_memories(query=user_message, user_id=user_id, limit=3),
            timeout=3.0,
        )
        if not memories:
            return ""

        lines = []
        for m in memories:
            text = m.get("memory", "") if isinstance(m, dict) else str(m)
            if text:
                lines.append(f"- {text}")

        return "User Memories (from previous conversations):\n" + "\n".join(lines) if lines else ""

    except asyncio.TimeoutError:
        logger.warning("Memory search timed out (3 s), skipping")
    except Exception as e:
        logger.warning("Error searching memories: %s", e)

    return ""


async def store_conversation_memory(
    user_message: str,
    ai_response: str,
    user_id: str,
) -> None:
    """Fire-and-forget: store user+assistant exchange in mem0."""
    svc = _get_memory_service()
    if not svc:
        return

    try:
        await svc.add_memory(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": ai_response},
            ],
            user_id=user_id,
        )
    except Exception as e:
        logger.warning("Error storing memory: %s", e)
