"""
Tenant provider service — key rotation, encryption, agent↔provider mapping.
Business logic only; routes delegate here.
"""
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.invalidation import CacheInvalidation
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.common.constants import ErrorCode
from app.config.settings import settings
from app.core.exceptions import CmsException
from app.models.provider import CmsProvider, CmsProviderKey, CmsAgentModel, CmsAgentProvider
from app.utils.encryption import encrypt_value, decrypt_value
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TenantProviderService:
    """Tenant-scoped provider key management with rotation + agent↔provider mapping."""

    # ── Provider list (system + org custom) ───────────────────────────────

    async def list_available_providers(self, db: AsyncSession, cache: CacheService, org_id: str) -> list[dict]:
        """List providers available to an org (system providers only for now)."""

        async def _fetch():
            result = await db.execute(
                select(CmsProvider)
                .where(CmsProvider.org_id.is_(None), CmsProvider.is_active.is_(True))
                .order_by(CmsProvider.name)
            )
            return [
                {
                    "id": str(p.id), "name": p.name, "slug": p.slug,
                    "api_base_url": p.api_base_url, "auth_type": p.auth_type,
                    "is_active": p.is_active, "created_at": p.created_at,
                }
                for p in result.scalars().all()
            ]

        return await cache.get_or_set(
            CacheKeys.system_providers(), _fetch, ttl=settings.CACHE_PROVIDER_TTL,
        ) or []

    # ── Provider Key CRUD ────────────────────────────────────────────────

    async def list_providers_with_keys(
        self, db: AsyncSession, cache: CacheService, org_id: str,
    ) -> list[dict]:
        """List providers that have ≥ 1 active key in this org. Cached."""

        async def _fetch():
            result = await db.execute(
                select(CmsProvider, CmsProviderKey)
                .join(CmsProviderKey, and_(
                    CmsProviderKey.provider_id == CmsProvider.id,
                    CmsProviderKey.org_id == org_id,
                    CmsProviderKey.is_active.is_(True),
                ))
                .where(CmsProvider.is_active.is_(True))
                .order_by(CmsProvider.name)
            )
            # Deduplicate providers (a provider may have multiple keys)
            seen = set()
            providers = []
            for provider, _key in result.all():
                if str(provider.id) in seen:
                    continue
                seen.add(str(provider.id))
                providers.append({
                    "id": str(provider.id),
                    "name": provider.name,
                    "slug": provider.slug,
                    "api_base_url": provider.api_base_url,
                })
            return providers

        return await cache.get_or_set(
            CacheKeys.org_providers_with_keys(org_id), _fetch,
            ttl=settings.CACHE_PROVIDER_TTL,
        ) or []

    async def list_keys(
        self, db: AsyncSession, cache: CacheService, org_id: str, provider_id: str,
    ) -> list[dict]:
        """List API keys for a provider in this org (masked)."""

        async def _fetch():
            result = await db.execute(
                select(CmsProviderKey)
                .where(
                    CmsProviderKey.org_id == org_id,
                    CmsProviderKey.provider_id == provider_id,
                )
                .order_by(CmsProviderKey.priority)
            )
            keys = []
            for k in result.scalars().all():
                try:
                    decrypted = decrypt_value(k.api_key_encrypted)
                    preview = f"...{decrypted[-4:]}"
                except Exception:
                    preview = "...****"

                keys.append({
                    "id": str(k.id), "provider_id": str(k.provider_id),
                    "org_id": str(k.org_id), "key_preview": preview,
                    "priority": k.priority, "is_active": k.is_active,
                    "last_used_at": k.last_used_at,
                    "cooldown_until": k.cooldown_until,
                    "created_at": k.created_at,
                })
            return keys

        return await cache.get_or_set(
            CacheKeys.provider_keys(org_id, provider_id), _fetch,
            ttl=settings.CACHE_PROVIDER_TTL,
        ) or []

    async def add_key(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, provider_id: str, api_key: str, priority: int = 1,
    ) -> dict:
        """Add an encrypted API key for a provider."""
        encrypted = encrypt_value(api_key)
        now = datetime.now(timezone.utc)

        key = CmsProviderKey(
            provider_id=provider_id, org_id=org_id,
            api_key_encrypted=encrypted, priority=priority,
            is_active=True, created_at=now,
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)

        await CacheInvalidation(cache).clear_provider_keys(org_id, provider_id)
        logger.info(f"Added provider key: org={org_id}, provider={provider_id}")

        return {
            "id": str(key.id), "provider_id": str(key.provider_id),
            "org_id": str(key.org_id), "key_preview": f"...{api_key[-4:]}",
            "priority": key.priority, "is_active": key.is_active,
            "last_used_at": None, "cooldown_until": None,
            "created_at": key.created_at,
        }

    async def update_key(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, key_id: str, **data,
    ) -> dict:
        """Update a provider key (priority, is_active)."""
        key = await db.get(CmsProviderKey, key_id)
        if not key or str(key.org_id) != org_id:
            raise CmsException(error_code=ErrorCode.PROVIDER_NOT_FOUND, detail="Provider key not found", status_code=404)

        for k, v in data.items():
            if v is not None:
                setattr(key, k, v)
        await db.commit()
        await db.refresh(key)

        await CacheInvalidation(cache).clear_provider_keys(org_id, str(key.provider_id))

        try:
            decrypted = decrypt_value(key.api_key_encrypted)
            preview = f"...{decrypted[-4:]}"
        except Exception:
            preview = "...****"

        return {
            "id": str(key.id), "provider_id": str(key.provider_id),
            "org_id": str(key.org_id), "key_preview": preview,
            "priority": key.priority, "is_active": key.is_active,
            "last_used_at": key.last_used_at,
            "cooldown_until": key.cooldown_until,
            "created_at": key.created_at,
        }

    async def delete_key(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, key_id: str,
    ) -> None:
        """Delete a provider key."""
        key = await db.get(CmsProviderKey, key_id)
        if not key or str(key.org_id) != org_id:
            raise CmsException(error_code=ErrorCode.PROVIDER_NOT_FOUND, detail="Provider key not found", status_code=404)

        provider_id = str(key.provider_id)
        await db.delete(key)
        await db.commit()

        await CacheInvalidation(cache).clear_provider_keys(org_id, provider_id)

    # ── Key Rotation ─────────────────────────────────────────────────────

    async def get_active_key(self, db: AsyncSession, org_id: str, provider_id: str) -> str:
        """Get the next available API key (skip cooldown keys). Returns decrypted key."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(CmsProviderKey)
            .where(
                CmsProviderKey.org_id == org_id,
                CmsProviderKey.provider_id == provider_id,
                CmsProviderKey.is_active.is_(True),
            )
            .order_by(CmsProviderKey.priority, CmsProviderKey.last_used_at.asc().nullsfirst())
        )
        keys = result.scalars().all()

        for key in keys:
            if key.cooldown_until and key.cooldown_until > now:
                continue
            # Mark as used
            key.last_used_at = now
            await db.commit()
            return decrypt_value(key.api_key_encrypted)

        raise CmsException(
            error_code="PROVIDER_KEY_EXHAUSTED",
            detail="All provider keys are in cooldown or inactive",
            status_code=503,
        )

    async def mark_key_cooldown(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, key_id: str, duration_seconds: int = 60,
    ) -> None:
        """Mark a key as in cooldown (e.g. after 429 rate limit)."""
        key = await db.get(CmsProviderKey, key_id)
        if not key or str(key.org_id) != org_id:
            return

        key.cooldown_until = datetime.now(timezone.utc).replace(
            second=datetime.now(timezone.utc).second
        )
        from datetime import timedelta
        key.cooldown_until = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
        await db.commit()

        await CacheInvalidation(cache).clear_provider_keys(org_id, str(key.provider_id))

    # ── Agent ↔ Provider ↔ Model Mapping ─────────────────────────────────

    async def list_agent_mappings(self, db: AsyncSession, org_id: str) -> list[dict]:
        """List agent ↔ provider ↔ model mappings for org."""
        result = await db.execute(
            select(CmsAgentProvider)
            .where(CmsAgentProvider.org_id == org_id)
        )
        return [
            {
                "id": str(m.id), "org_id": str(m.org_id),
                "agent_id": str(m.agent_id), "provider_id": str(m.provider_id),
                "model_id": str(m.model_id), "config_override": m.config_override,
                "is_active": m.is_active,
            }
            for m in result.scalars().all()
        ]

    async def create_agent_mapping(
        self, db: AsyncSession, org_id: str,
        agent_id: str, provider_id: str, model_id: str,
        config_override: dict | None = None,
    ) -> dict:
        """Create agent ↔ provider ↔ model mapping."""
        # Check for duplicate
        existing = await db.execute(
            select(CmsAgentProvider).where(
                CmsAgentProvider.org_id == org_id,
                CmsAgentProvider.agent_id == agent_id,
                CmsAgentProvider.provider_id == provider_id,
            )
        )
        if existing.scalar_one_or_none():
            raise CmsException(
                error_code="AGENT_PROVIDER_EXISTS",
                detail="Agent-provider mapping already exists",
                status_code=409,
            )

        mapping = CmsAgentProvider(
            org_id=org_id, agent_id=agent_id,
            provider_id=provider_id, model_id=model_id,
            config_override=config_override, is_active=True,
        )
        db.add(mapping)
        await db.commit()
        await db.refresh(mapping)

        return {
            "id": str(mapping.id), "org_id": str(mapping.org_id),
            "agent_id": str(mapping.agent_id), "provider_id": str(mapping.provider_id),
            "model_id": str(mapping.model_id), "config_override": mapping.config_override,
            "is_active": mapping.is_active,
        }

    async def update_agent_mapping(
        self, db: AsyncSession, org_id: str, mapping_id: str, **data,
    ) -> dict:
        """Update agent ↔ provider ↔ model mapping."""
        mapping = await db.get(CmsAgentProvider, mapping_id)
        if not mapping or str(mapping.org_id) != org_id:
            raise CmsException(error_code="AGENT_PROVIDER_NOT_FOUND", detail="Mapping not found", status_code=404)

        for k, v in data.items():
            if v is not None:
                setattr(mapping, k, v)
        await db.commit()
        await db.refresh(mapping)

        return {
            "id": str(mapping.id), "org_id": str(mapping.org_id),
            "agent_id": str(mapping.agent_id), "provider_id": str(mapping.provider_id),
            "model_id": str(mapping.model_id), "config_override": mapping.config_override,
            "is_active": mapping.is_active,
        }

    async def delete_agent_mapping(self, db: AsyncSession, org_id: str, mapping_id: str) -> None:
        """Delete agent ↔ provider ↔ model mapping."""
        mapping = await db.get(CmsAgentProvider, mapping_id)
        if not mapping or str(mapping.org_id) != org_id:
            raise CmsException(error_code="AGENT_PROVIDER_NOT_FOUND", detail="Mapping not found", status_code=404)

        await db.delete(mapping)
        await db.commit()

    # ── Models ───────────────────────────────────────────────────────────

    async def list_models(self, db: AsyncSession, provider_id: str) -> list[dict]:
        """List models for a provider."""
        result = await db.execute(
            select(CmsAgentModel)
            .where(CmsAgentModel.provider_id == provider_id, CmsAgentModel.is_active.is_(True))
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


# Singleton
tenant_provider_svc = TenantProviderService()
