"""
System API — Agent CRUD (superuser only).
Thin router — all logic in agent_svc.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_superuser
from app.common.types import CurrentUser
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentOrgAssignment,
    AgentOrgResponse,
    AgentToolResponse,
    SetPublicBody,
)
from app.schemas.common import SuccessResponse
from app.cache.service import CacheService
from app.services.agent import agent_svc
from app.services.audit import audit_svc

router = APIRouter(prefix="/agents", tags=["system-agents"])


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """List all system agents."""
    return await agent_svc.list_system(db, cache)


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Create a system agent."""
    agent = await agent_svc.create(db, cache, **data.model_dump())
    await audit_svc.log_action(db, user.user_id, "create", "agent", str(agent.id), new_values=data.model_dump())
    return agent


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_superuser),
):
    """Get a system agent."""
    return await agent_svc.get(db, agent_id)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Update a system agent."""
    agent = await agent_svc.update(db, cache, agent_id, **data.model_dump(exclude_unset=True))
    await audit_svc.log_action(db, user.user_id, "update", "agent", str(agent.id), new_values=data.model_dump(exclude_unset=True))
    return agent


@router.delete("/{agent_id}", response_model=SuccessResponse)
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Delete a system agent."""
    await agent_svc.delete(db, cache, agent_id)
    await audit_svc.log_action(db, user.user_id, "delete", "agent", agent_id)
    return {"message": "Agent deleted successfully"}
    

@router.put("/{agent_id}/set-public", response_model=AgentResponse)
async def set_agent_public(
    agent_id: str,
    body: SetPublicBody,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Toggle is_public for a system agent."""
    agent = await agent_svc.set_public(db, cache, agent_id, body.is_public)
    await audit_svc.log_action(db, user.user_id, "set_public", "agent", agent_id, new_values={"is_public": body.is_public})
    return agent


# ── Org assignment ────────────────────────────────────────────────────


@router.get("/{agent_id}/orgs", response_model=list[AgentOrgResponse])
async def list_agent_orgs(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_superuser),
):
    """List orgs assigned to a system agent."""
    return await agent_svc.list_assigned_orgs(db, agent_id)


@router.put("/{agent_id}/orgs", response_model=list[AgentOrgResponse])
async def set_agent_orgs(
    agent_id: str,
    data: AgentOrgAssignment,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Set org assignment for a system agent."""
    result = await agent_svc.set_assigned_orgs(db, cache, agent_id, data.org_ids)
    await audit_svc.log_action(db, user.user_id, "assign_orgs", "agent", agent_id, new_values={"org_ids": data.org_ids})
    return result


# ── Agent tools ───────────────────────────────────────────────────────


@router.get("/{agent_id}/tools", response_model=list[AgentToolResponse])
async def list_agent_tools(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_superuser),
):
    """List tools for a system agent."""
    return await agent_svc.list_agent_tools(db, agent_id)
