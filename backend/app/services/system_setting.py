"""
System settings service — key-value config with Redis caching.
System settings rarely change → long TTL with invalidation on mutation.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CmsException
from app.config.settings import settings
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation
from app.models.system_setting import CmsSystemSetting
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SystemSettingService:
    """System settings CRUD with Redis cache."""

    async def list_all(self, db: AsyncSession, cache: CacheService) -> list[dict]:
        """List all system settings. Cached."""

        async def _fetch():
            result = await db.execute(
                select(CmsSystemSetting).order_by(CmsSystemSetting.key)
            )
            return [
                {
                    "id": str(s.id),
                    "key": s.key,
                    "value": s.value,
                    "description": s.description,
                }
                for s in result.scalars().all()
            ]

        return await cache.get_or_set(
            CacheKeys.system_settings(), _fetch, ttl=settings.CACHE_DEFAULT_TTL
        ) or []

    async def get_by_key(self, db: AsyncSession, cache: CacheService, key: str) -> dict:
        """Get a setting by key. Cached."""

        async def _fetch():
            result = await db.execute(
                select(CmsSystemSetting).where(CmsSystemSetting.key == key)
            )
            setting = result.scalar_one_or_none()
            if not setting:
                return None
            return {
                "id": str(setting.id),
                "key": setting.key,
                "value": setting.value,
                "description": setting.description,
            }

        result = await cache.get_or_set(
            CacheKeys.system_setting(key), _fetch, ttl=settings.CACHE_DEFAULT_TTL
        )
        if not result:
            raise CmsException(
                error_code="SETTING_NOT_FOUND",
                detail=f"Setting '{key}' not found",
                status_code=404,
            )
        return result

    async def upsert(
        self, db: AsyncSession, cache: CacheService, key: str, value, description: str | None = None
    ) -> tuple[dict, dict | None]:
        """Create or update a setting. Returns (new_data, old_data). Invalidates cache."""
        result = await db.execute(
            select(CmsSystemSetting).where(CmsSystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        old_values = None

        if setting:
            old_values = {"value": setting.value}
            setting.value = value
            if description is not None:
                setting.description = description
        else:
            setting = CmsSystemSetting(key=key, value=value, description=description)
            db.add(setting)

        await db.commit()
        await db.refresh(setting)

        # Invalidate cache
        invalidation = CacheInvalidation(cache)
        await invalidation.clear_system_setting(key)

        new_data = {
            "id": str(setting.id),
            "key": setting.key,
            "value": setting.value,
            "description": setting.description,
        }
        return new_data, old_values


# Singleton
setting_svc = SystemSettingService()
