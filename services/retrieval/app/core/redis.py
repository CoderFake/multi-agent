"""Redis client for task queue, progress tracking, and dedup locks.

Usage:
    from app.core.redis import get_redis, update_task_progress, acquire_lock
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import redis

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None

# Key prefixes
QUEUE_KEY = "idx:queue"
TASK_KEY_PREFIX = "idx:task:"
LOCK_KEY_PREFIX = "idx:lock:"


def get_redis() -> redis.Redis:
    """Get or create Redis client singleton."""
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        _client.ping()
        logger.info("Redis connected: %s", settings.REDIS_URL)
    return _client


def close_redis() -> None:
    """Close Redis connection."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("Redis connection closed")


# ── Task Progress ─────────────────────────────────────────────────────

def update_task_progress(
    job_id: str,
    status: str,
    progress: int,
    message: str = "",
    total_chunks: int = 0,
    processed_chunks: int = 0,
    error: str | None = None,
    document_id: str = "",
) -> None:
    """Update task progress in Redis."""
    client = get_redis()
    key = f"{TASK_KEY_PREFIX}{job_id}"
    data = {
        "job_id": job_id,
        "document_id": document_id,
        "status": status,
        "progress": progress,
        "message": message,
        "total_chunks": total_chunks,
        "processed_chunks": processed_chunks,
        "error": error,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    client.setex(key, settings.TASK_TTL, json.dumps(data))


def get_task_progress(job_id: str) -> Optional[dict]:
    """Get task progress from Redis."""
    client = get_redis()
    key = f"{TASK_KEY_PREFIX}{job_id}"
    raw = client.get(key)
    return json.loads(raw) if raw else None


# ── Dedup Lock ────────────────────────────────────────────────────────

def acquire_lock(org_id: str, file_hash: str) -> bool:
    """Acquire dedup lock. Returns True if lock acquired (not duplicate)."""
    client = get_redis()
    key = f"{LOCK_KEY_PREFIX}{org_id}:{file_hash}"
    return bool(client.set(key, "1", nx=True, ex=settings.LOCK_TTL))


def release_lock(org_id: str, file_hash: str) -> None:
    """Release dedup lock."""
    client = get_redis()
    key = f"{LOCK_KEY_PREFIX}{org_id}:{file_hash}"
    client.delete(key)


# ── Queue ─────────────────────────────────────────────────────────────

def push_task(task_payload: dict) -> None:
    """Push a task to the indexing queue (called by backend)."""
    client = get_redis()
    client.lpush(QUEUE_KEY, json.dumps(task_payload))


def pop_task(timeout: int = 5) -> Optional[dict]:
    """Blocking pop a task from the queue (called by worker)."""
    client = get_redis()
    result = client.brpop(QUEUE_KEY, timeout=timeout)
    if result:
        _, raw = result
        return json.loads(raw)
    return None
