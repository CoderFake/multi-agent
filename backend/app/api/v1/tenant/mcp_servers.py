"""
Tenant MCP Server + Tool API — CRUD for custom MCP servers and tools.
Router = thin delegation only. All logic in tenant_mcp_svc.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_org_membership
from app.common.types import CurrentUser
from app.cache.service import CacheService
from app.schemas.mcp import McpServerCreate, McpServerUpdate, ToolCreate
from app.services.tenant_mcp import tenant_mcp_svc

router = APIRouter(prefix="/mcp-servers", tags=["tenant-mcp"])


@router.get("")
async def list_mcp_servers(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """List MCP servers in the current org."""
    return await tenant_mcp_svc.list_servers(db, cache, user.org_id)


@router.post("", status_code=201)
async def create_mcp_server(
    data: McpServerCreate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Create a custom MCP server in the org."""
    return await tenant_mcp_svc.create_server(
        db, cache, user.org_id,
        data.codename, data.display_name, data.transport, data.connection_config,
    )


@router.put("/{server_id}")
async def update_mcp_server(
    server_id: str,
    data: McpServerUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Update a custom MCP server."""
    return await tenant_mcp_svc.update_server(
        db, cache, user.org_id, server_id,
        **data.model_dump(exclude_unset=True),
    )


@router.delete("/{server_id}", status_code=204)
async def delete_mcp_server(
    server_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_org_membership),
):
    """Delete a custom MCP server."""
    await tenant_mcp_svc.delete_server(db, cache, user.org_id, server_id)


# ── Tool CRUD ────────────────────────────────────────────────────────────

@router.get("/{server_id}/tools")
async def list_tools(
    server_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_org_membership),
):
    """List tools for a MCP server."""
    return await tenant_mcp_svc.list_tools(db, user.org_id, server_id)


@router.post("/{server_id}/tools", status_code=201)
async def create_tool(
    server_id: str,
    data: ToolCreate,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_org_membership),
):
    """Create a tool for a MCP server."""
    return await tenant_mcp_svc.create_tool(
        db, user.org_id, server_id,
        data.codename, data.display_name, data.description, data.input_schema,
    )


@router.delete("/{server_id}/tools/{tool_id}", status_code=204)
async def delete_tool(
    server_id: str,
    tool_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_org_membership),
):
    """Delete a tool from a MCP server."""
    await tenant_mcp_svc.delete_tool(db, user.org_id, server_id, tool_id)
