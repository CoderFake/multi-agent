"""
Tenant Agent API — custom agent CRUD + system agent enable/disable.
Router = thin delegation only. All logic in tenant_agent_svc.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_permission
from app.common.types import CurrentUser
from app.cache.service import CacheService
from app.schemas.agent import AgentCreate, AgentUpdate, SetAgentProviderBody
from app.services.tenant_agent import tenant_agent_svc
from app.services.audit import audit_svc

router = APIRouter(prefix="/agents", tags=["tenant-agents"])


@router.get("")
async def list_agents(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("agent.view")),
):
    """List available agents: system enabled + org custom agents."""
    return await tenant_agent_svc.list_agents(db, cache, user.org_id)


@router.post("", status_code=201)
async def create_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("agent.create")),
):
    """Create a custom agent within the org."""
    result = await tenant_agent_svc.create_agent(
        db, cache, user.org_id,
        data.codename, data.display_name, data.description, data.default_config,
        provider_id=data.provider_id, model_id=data.model_id,
    )
    await audit_svc.log_action(
        db, user.user_id, "create", "agent", result["id"],
        org_id=user.org_id, new_values=data.model_dump(),
    )
    return result


@router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("agent.update")),
):
    """Update a custom agent (org-owned only)."""
    result = await tenant_agent_svc.update_agent(
        db, cache, user.org_id, agent_id,
        **data.model_dump(exclude_unset=True),
    )
    await audit_svc.log_action(
        db, user.user_id, "update", "agent", agent_id,
        org_id=user.org_id, new_values=data.model_dump(exclude_unset=True),
    )
    return result


@router.put("/{agent_id}/provider")
async def set_agent_provider(
    agent_id: str,
    data: SetAgentProviderBody,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("agent.update")),
):
    """Set/update provider+model for any agent (system or custom) in this org."""
    result = await tenant_agent_svc.set_agent_provider(
        db, cache, user.org_id, agent_id, data.provider_id, data.model_id,
    )
    await audit_svc.log_action(
        db, user.user_id, "update", "agent_provider", agent_id,
        org_id=user.org_id, new_values=data.model_dump(),
    )
    return result


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("agent.delete")),
):
    """Delete a custom agent (org-owned only)."""
    await tenant_agent_svc.delete_agent(db, cache, user.org_id, agent_id)
    await audit_svc.log_action(
        db, user.user_id, "delete", "agent", agent_id, org_id=user.org_id,
    )


@router.post("/system/{agent_id}/enable", status_code=200)
async def enable_system_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("agent.update")),
):
    """Enable a system agent for this org."""
    result = await tenant_agent_svc.enable_system_agent(db, cache, user.org_id, agent_id)
    await audit_svc.log_action(
        db, user.user_id, "enable", "system_agent", agent_id, org_id=user.org_id,
    )
    return result


@router.post("/system/{agent_id}/disable", status_code=200)
async def disable_system_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("agent.update")),
):
    """Disable a system agent for this org."""
    result = await tenant_agent_svc.disable_system_agent(db, cache, user.org_id, agent_id)
    await audit_svc.log_action(
        db, user.user_id, "disable", "system_agent", agent_id, org_id=user.org_id,
    )
    return result
