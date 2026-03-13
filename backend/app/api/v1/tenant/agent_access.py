"""
Tenant Agent Access Control API.
Routes = validation + service delegation only.
Manages: Agent ↔ MCP, Group ↔ Agent, Group ↔ Tool access.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_org_membership
from app.common.types import CurrentUser
from app.cache.service import CacheService
from app.schemas.agent_access import (
    AgentMcpAssign, AgentMcpEnvUpdate, GroupAgentAssign,
    GroupToolToggle, GroupToolBulkToggle,
    OrgAgentPublicToggle,
)
from app.services.tenant_agent_access import tenant_agent_access_svc

router = APIRouter(prefix="/access", tags=["tenant-access-control"])


# ── Available MCP Servers ────────────────────────────────────────────────

@router.get("/available-mcp-servers")
async def list_available_mcp_servers(
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_org_membership),
):
    """List MCP servers available to this org (public + assigned)."""
    return await tenant_agent_access_svc.list_available_mcp_servers(db, user.org_id)


# ── Agent ↔ MCP Server ──────────────────────────────────────────────────

@router.get("/agents/{agent_id}/mcp-servers")
async def list_agent_mcp_servers(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """List MCP servers assigned to an agent."""
    return await tenant_agent_access_svc.list_agent_mcp_servers(db, cache, user.org_id, agent_id)


@router.post("/agents/{agent_id}/mcp-servers", status_code=201)
async def assign_mcp_to_agent(
    agent_id: str,
    data: AgentMcpAssign,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Assign an MCP server to an agent."""
    return await tenant_agent_access_svc.assign_mcp_to_agent(
        db, cache, user.org_id, agent_id, data.mcp_server_id, data.env_overrides,
    )


@router.delete("/agents/{agent_id}/mcp-servers/{mcp_server_id}", status_code=204)
async def revoke_mcp_from_agent(
    agent_id: str,
    mcp_server_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Revoke an MCP server from an agent."""
    await tenant_agent_access_svc.revoke_mcp_from_agent(
        db, cache, user.org_id, agent_id, mcp_server_id,
    )


@router.patch("/agents/{agent_id}/mcp-servers/{mcp_server_id}/env")
async def update_agent_mcp_env(
    agent_id: str,
    mcp_server_id: str,
    data: AgentMcpEnvUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Update env overrides for an agent-MCP link."""
    return await tenant_agent_access_svc.update_agent_mcp_env(
        db, cache, user.org_id, agent_id, mcp_server_id, data.env_overrides,
    )


# ── Agent is_public toggle ──────────────────────────────────────────────

@router.patch("/agents/{agent_id}/public")
async def toggle_agent_public(
    agent_id: str,
    data: OrgAgentPublicToggle,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Toggle agent public/restricted visibility."""
    return await tenant_agent_access_svc.toggle_agent_public(
        db, cache, user.org_id, agent_id, data.is_public,
    )


# ── Group ↔ Agent ────────────────────────────────────────────────────────

@router.get("/groups/{group_id}/agents")
async def list_group_agents(
    group_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """List agents assigned to a group."""
    return await tenant_agent_access_svc.list_group_agents(db, cache, user.org_id, group_id)


@router.post("/groups/{group_id}/agents", status_code=201)
async def assign_agents_to_group(
    group_id: str,
    data: GroupAgentAssign,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Assign agents to a group."""
    return await tenant_agent_access_svc.assign_agents_to_group(
        db, cache, user.org_id, group_id, data.agent_ids,
    )


@router.delete("/groups/{group_id}/agents/{agent_id}", status_code=204)
async def revoke_agent_from_group(
    group_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Revoke agent access from a group."""
    await tenant_agent_access_svc.revoke_agent_from_group(
        db, cache, user.org_id, group_id, agent_id,
    )


# ── Group ↔ Tool Access ─────────────────────────────────────────────────

@router.get("/groups/{group_id}/tools")
async def list_group_tool_access(
    group_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """List tool access settings for a group."""
    return await tenant_agent_access_svc.list_group_tool_access(db, cache, user.org_id, group_id)


@router.put("/groups/{group_id}/tools")
async def bulk_toggle_tools(
    group_id: str,
    data: GroupToolBulkToggle,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Bulk toggle tool access for a group."""
    return await tenant_agent_access_svc.bulk_toggle_tools(
        db, cache, user.org_id, group_id,
        [e.model_dump() for e in data.entries],
    )


@router.patch("/groups/{group_id}/tools/{tool_id}")
async def toggle_tool_access(
    group_id: str,
    tool_id: str,
    data: GroupToolToggle,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Toggle a single tool's access for a group."""
    return await tenant_agent_access_svc.toggle_tool_access(
        db, cache, user.org_id, group_id, tool_id, data.is_enabled,
    )
