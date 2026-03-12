"""
System provider service — business logic for system-level providers.
Data rarely changes → cached in Redis with CACHE_PROVIDER_TTL.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.config.settings import settings
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation
from app.models.provider import CmsProvider
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ProviderService:
    """System provider CRUD with Redis cache."""

    async def list_system(self, db: AsyncSession, cache: CacheService) -> list[dict]:
        """List all system providers. Cached."""

        async def _fetch():
            result = await db.execute(
                select(CmsProvider).where(CmsProvider.org_id.is_(None)).order_by(CmsProvider.created_at.desc())
            )
            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "slug": p.slug,
                    "api_base_url": p.api_base_url,
                    "auth_type": p.auth_type,
                    "is_active": p.is_active,
                    "org_id": None,
                    "created_at": p.created_at,
                }
                for p in result.scalars().all()
            ]

        return await cache.get_or_set(
            CacheKeys.system_providers(), _fetch, ttl=settings.CACHE_PROVIDER_TTL
        ) or []

    async def create(self, db: AsyncSession, cache: CacheService, **data) -> CmsProvider:
        """Create a system provider. Invalidates cache."""
        existing = await db.execute(
            select(CmsProvider).where(CmsProvider.slug == data["slug"], CmsProvider.org_id.is_(None))
        )
        if existing.scalar_one_or_none():
            raise CmsException(error_code="PROVIDER_SLUG_EXISTS", detail="Provider slug exists", status_code=409)

        provider = CmsProvider(org_id=None, is_active=True, **data)
        db.add(provider)
        await db.commit()
        await db.refresh(provider)

        await CacheInvalidation(cache).clear_system_providers()
        return provider

    async def get(self, db: AsyncSession, provider_id: str) -> CmsProvider:
        """Get a system provider."""
        provider = await db.get(CmsProvider, provider_id)
        if not provider or provider.org_id is not None:
            raise CmsException(error_code=ErrorCode.PROVIDER_NOT_FOUND, detail="Provider not found", status_code=404)
        return provider

    async def update(self, db: AsyncSession, cache: CacheService, provider_id: str, **data) -> CmsProvider:
        """Update a system provider. Invalidates cache."""
        provider = await self.get(db, provider_id)
        for key, value in data.items():
            if value is not None:
                setattr(provider, key, value)
        await db.commit()
        await db.refresh(provider)

        await CacheInvalidation(cache).clear_system_providers()
        return provider

    async def delete(self, db: AsyncSession, cache: CacheService, provider_id: str) -> None:
        """Delete a system provider. Invalidates cache."""
        provider = await self.get(db, provider_id)
        await db.delete(provider)
        await db.commit()

        await CacheInvalidation(cache).clear_system_providers()


# Singleton
provider_svc = ProviderService()
