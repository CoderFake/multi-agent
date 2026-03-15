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
from app.models.provider import CmsProvider, CmsAgentModel
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

    # ── Model CRUD ───────────────────────────────────────────────────────

    async def list_models(self, db: AsyncSession, provider_id: str) -> list[dict]:
        """List models for a system provider."""
        await self.get(db, provider_id)  # verify exists
        result = await db.execute(
            select(CmsAgentModel)
            .where(CmsAgentModel.provider_id == provider_id)
            .order_by(CmsAgentModel.name)
        )
        return [
            {
                "id": str(m.id), "provider_id": str(m.provider_id),
                "name": m.name, "model_type": m.model_type,
                "context_window": m.context_window,
                "pricing_per_1m_tokens": float(m.pricing_per_1m_tokens) if m.pricing_per_1m_tokens else None,
                "is_active": m.is_active, "created_at": m.created_at,
            }
            for m in result.scalars().all()
        ]

    async def create_model(
        self, db: AsyncSession, cache: CacheService,
        provider_id: str, name: str, model_type: str = "chat",
        context_window: int = None, pricing_per_1m_tokens: float = None,
    ) -> CmsAgentModel:
        """Create a model for a system provider."""
        await self.get(db, provider_id)
        model = CmsAgentModel(
            provider_id=provider_id,
            name=name, model_type=model_type,
            context_window=context_window,
            pricing_per_1m_tokens=pricing_per_1m_tokens,
            is_active=True,
        )
        db.add(model)
        await db.commit()
        await db.refresh(model)
        await self._invalidate_model_caches(cache)
        logger.info(f"Model created: {name} for provider {provider_id}")
        return model

    async def update_model(
        self, db: AsyncSession, cache: CacheService,
        provider_id: str, model_id: str, **data,
    ) -> CmsAgentModel:
        """Update a model."""
        model = await self._get_model(db, provider_id, model_id)
        for key, value in data.items():
            if value is not None and hasattr(model, key):
                setattr(model, key, value)
        await db.commit()
        await db.refresh(model)
        await self._invalidate_model_caches(cache)
        return model

    async def delete_model(
        self, db: AsyncSession, cache: CacheService,
        provider_id: str, model_id: str,
    ) -> None:
        """Delete a model."""
        model = await self._get_model(db, provider_id, model_id)
        await db.delete(model)
        await db.commit()
        await self._invalidate_model_caches(cache)
        logger.info(f"Model deleted: {model.name}")

    async def _get_model(self, db: AsyncSession, provider_id: str, model_id: str) -> CmsAgentModel:
        """Get a model by ID within a provider."""
        result = await db.execute(
            select(CmsAgentModel).where(
                CmsAgentModel.id == model_id,
                CmsAgentModel.provider_id == provider_id,
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            raise CmsException(error_code=ErrorCode.PROVIDER_NOT_FOUND, detail="Model not found", status_code=404)
        return model

    async def _invalidate_model_caches(self, cache: CacheService) -> None:
        """Invalidate tenant provider caches when system models change."""
        inv = CacheInvalidation(cache)
        await inv.clear_system_providers()
        # Tenant caches that depend on models
        await cache.delete_pattern("org_providers_with_keys:*")


# Singleton
provider_svc = ProviderService()
