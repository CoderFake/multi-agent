"""
Generic Redis cache service.
Provides get/set/delete operations with JSON serialization and read-through pattern.
Copied from embed_chatbot with added get_or_set for read-through caching.
"""
from typing import Optional, Any, List, Callable, Awaitable
import json

from redis.asyncio import Redis

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """Redis cache service with common operations."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, key: str, as_json: bool = True) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
            if as_json:
                return json.loads(value)
            return value
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        as_json: bool = True,
    ) -> bool:
        """Set value in cache with optional TTL."""
        try:
            if as_json:
                serialized = json.dumps(value, ensure_ascii=False, default=str)
            else:
                serialized = value
            cache_ttl = ttl or settings.CACHE_DEFAULT_TTL
            await self.redis.setex(key, cache_ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        try:
            cursor = 0
            deleted_count = 0
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor, match=pattern, count=100
                )
                if keys:
                    deleted_count += await self.redis.delete(*keys)
                if cursor == 0:
                    break
            logger.info(f"Deleted {deleted_count} keys matching pattern: {pattern}")
            return deleted_count
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists check error for key {key}: {e}")
            return False

    async def get_or_set(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[Any]],
        ttl: Optional[int] = None,
        as_json: bool = True,
    ) -> Optional[Any]:
        """
        Read-through cache: get from cache, or fetch and cache.

        Args:
            key: Cache key
            fetcher: Async function to fetch data on cache miss
            ttl: Cache TTL in seconds
            as_json: JSON serialization

        Returns:
            Cached or freshly fetched value
        """
        cached = await self.get(key, as_json=as_json)
        if cached is not None:
            return cached

        value = await fetcher()
        if value is not None:
            await self.set(key, value, ttl=ttl, as_json=as_json)
        return value

    async def get_many(self, keys: List[str], as_json: bool = True) -> dict:
        """Get multiple values from cache."""
        try:
            if not keys:
                return {}
            values = await self.redis.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value is None:
                    result[key] = None
                elif as_json:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        result[key] = value
                else:
                    result[key] = value
            return result
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {key: None for key in keys}

    async def set_many(
        self,
        mapping: dict,
        ttl: Optional[int] = None,
        as_json: bool = True,
    ) -> bool:
        """Set multiple key-value pairs."""
        try:
            if not mapping:
                return True
            pipe = self.redis.pipeline()
            cache_ttl = ttl or settings.CACHE_DEFAULT_TTL
            for key, value in mapping.items():
                if as_json:
                    serialized = json.dumps(value, ensure_ascii=False, default=str)
                else:
                    serialized = value
                pipe.setex(key, cache_ttl, serialized)
            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
