"""
System API — Provider management (superuser only).
Providers are pre-seeded in DB init — only list, get, update allowed.
Thin router — all logic in provider_svc.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_superuser
from app.common.types import CurrentUser
from app.schemas.provider import ProviderUpdate, ProviderResponse
from app.cache.service import CacheService
from app.services.provider import provider_svc
from app.services.audit import audit_svc

router = APIRouter(prefix="/providers", tags=["system-providers"])


@router.get("", response_model=list[ProviderResponse])
async def list_providers(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """List all system providers."""
    return await provider_svc.list_system(db, cache)


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_superuser),
):
    """Get a system provider."""
    return await provider_svc.get(db, provider_id)


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: str,
    data: ProviderUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Update a system provider (API keys, active status, etc.)."""
    provider = await provider_svc.update(db, cache, provider_id, **data.model_dump(exclude_unset=True))
    await audit_svc.log_action(db, user.user_id, "update", "provider", str(provider.id), new_values=data.model_dump(exclude_unset=True))
    return provider
