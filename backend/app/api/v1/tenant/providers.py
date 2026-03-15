"""
Tenant Provider API — provider keys (rotation), agent↔provider mapping.
Router = thin delegation layer. All logic in tenant_provider_svc.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_permission
from app.common.types import CurrentUser
from app.cache.service import CacheService
from app.schemas.provider import (
    ProviderKeyCreate, ProviderKeyUpdate, ProviderKeyResponse,
    AgentProviderCreate, AgentProviderUpdate, AgentProviderResponse,
)
from app.services.tenant_provider import tenant_provider_svc
from app.services.audit import audit_svc

router = APIRouter(prefix="/providers", tags=["tenant-providers"])


# ── Available Providers ──────────────────────────────────────────────────

@router.get("")
async def list_providers(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("provider.view")),
):
    """List available providers (system + org custom)."""
    return await tenant_provider_svc.list_available_providers(db, cache, user.org_id)


@router.get("/with-keys")
async def list_providers_with_keys(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("provider.view")),
):
    """List providers that have ≥ 1 active API key in this org. For agent create/edit."""
    return await tenant_provider_svc.list_providers_with_keys(db, cache, user.org_id)


# ── Provider Keys ────────────────────────────────────────────────────────

@router.get("/{provider_id}/keys")
async def list_provider_keys(
    provider_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("provider_key.view")),
):
    """List API keys for a provider (masked)."""
    return await tenant_provider_svc.list_keys(db, cache, user.org_id, provider_id)


@router.post("/{provider_id}/keys", status_code=201)
async def add_provider_key(
    provider_id: str,
    data: ProviderKeyCreate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("provider_key.create")),
):
    """Add an API key for a provider (encrypted at rest)."""
    result = await tenant_provider_svc.add_key(
        db, cache, user.org_id, provider_id, data.api_key, data.priority,
    )
    await audit_svc.log_action(
        db, user.user_id, "create", "provider_key", result["id"],
        org_id=user.org_id, new_values={"provider_id": provider_id, "priority": data.priority},
    )
    return result


@router.put("/keys/{key_id}")
async def update_provider_key(
    key_id: str,
    data: ProviderKeyUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("provider_key.update")),
):
    """Update a provider key (priority, active status)."""
    result = await tenant_provider_svc.update_key(
        db, cache, user.org_id, key_id, **data.model_dump(exclude_unset=True),
    )
    await audit_svc.log_action(
        db, user.user_id, "update", "provider_key", key_id,
        org_id=user.org_id, new_values=data.model_dump(exclude_unset=True),
    )
    return result


@router.delete("/keys/{key_id}", status_code=204)
async def delete_provider_key(
    key_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("provider_key.delete")),
):
    """Delete a provider key."""
    await tenant_provider_svc.delete_key(db, cache, user.org_id, key_id)
    await audit_svc.log_action(
        db, user.user_id, "delete", "provider_key", key_id, org_id=user.org_id,
    )


# ── Provider Models ──────────────────────────────────────────────────────

@router.get("/{provider_id}/models")
async def list_models(
    provider_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("provider.view")),
):
    """List models for a provider."""
    return await tenant_provider_svc.list_models(db, provider_id)


# ── Agent ↔ Provider ↔ Model Mapping ─────────────────────────────────────

@router.get("/agent-mapping")
async def list_agent_mappings(
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("provider.view")),
):
    """List agent ↔ provider ↔ model mappings for org."""
    return await tenant_provider_svc.list_agent_mappings(db, user.org_id)


@router.post("/agent-mapping", status_code=201)
async def create_agent_mapping(
    data: AgentProviderCreate,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("agent.update")),
):
    """Create agent ↔ provider ↔ model mapping."""
    result = await tenant_provider_svc.create_agent_mapping(
        db, user.org_id, data.agent_id, data.provider_id, data.model_id, data.config_override,
    )
    await audit_svc.log_action(
        db, user.user_id, "create", "agent_provider", result["id"],
        org_id=user.org_id, new_values=data.model_dump(),
    )
    return result


@router.put("/agent-mapping/{mapping_id}")
async def update_agent_mapping(
    mapping_id: str,
    data: AgentProviderUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("agent.update")),
):
    """Update agent ↔ provider ↔ model mapping."""
    result = await tenant_provider_svc.update_agent_mapping(
        db, user.org_id, mapping_id, **data.model_dump(exclude_unset=True),
    )
    await audit_svc.log_action(
        db, user.user_id, "update", "agent_provider", mapping_id,
        org_id=user.org_id, new_values=data.model_dump(exclude_unset=True),
    )
    return result


@router.delete("/agent-mapping/{mapping_id}", status_code=204)
async def delete_agent_mapping(
    mapping_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("agent.update")),
):
    """Delete agent ↔ provider ↔ model mapping."""
    await tenant_provider_svc.delete_agent_mapping(db, user.org_id, mapping_id)
    await audit_svc.log_action(
        db, user.user_id, "delete", "agent_provider", mapping_id, org_id=user.org_id,
    )
