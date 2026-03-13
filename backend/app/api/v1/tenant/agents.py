"""
Tenant Agent API — custom agent CRUD + system agent enable/disable.
Router = thin delegation only. All logic in tenant_agent_svc.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_org_membership
from app.common.types import CurrentUser
from app.cache.service import CacheService
from app.schemas.agent import AgentCreate, AgentUpdate
from app.services.tenant_agent import tenant_agent_svc

router = APIRouter(prefix="/agents", tags=["tenant-agents"])


@router.get("")
async def list_agents(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """List available agents: system enabled + org custom agents."""
    return await tenant_agent_svc.list_agents(db, cache, user.org_id)


@router.post("", status_code=201)
async def create_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Create a custom agent within the org."""
    return await tenant_agent_svc.create_agent(
        db, cache, user.org_id,
        data.codename, data.display_name, data.description, data.default_config,
    )


@router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Update a custom agent (org-owned only)."""
    return await tenant_agent_svc.update_agent(
        db, cache, user.org_id, agent_id,
        **data.model_dump(exclude_unset=True),
    )


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Delete a custom agent (org-owned only)."""
    await tenant_agent_svc.delete_agent(db, cache, user.org_id, agent_id)


@router.post("/system/{agent_id}/enable", status_code=200)
async def enable_system_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Enable a system agent for this org."""
    return await tenant_agent_svc.enable_system_agent(db, cache, user.org_id, agent_id)


@router.post("/system/{agent_id}/disable", status_code=200)
async def disable_system_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Disable a system agent for this org."""
    return await tenant_agent_svc.disable_system_agent(db, cache, user.org_id, agent_id)
