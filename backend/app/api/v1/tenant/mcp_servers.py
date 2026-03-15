"""
Tenant MCP Server + Tool API — CRUD for custom MCP servers and tools.
Router = thin delegation only. All logic in tenant_mcp_svc.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_permission
from app.common.types import CurrentUser
from app.cache.service import CacheService
from app.schemas.mcp import McpServerCreate, McpServerUpdate, ToolCreate
from app.services.tenant_mcp import tenant_mcp_svc
from app.services.audit import audit_svc

router = APIRouter(prefix="/mcp-servers", tags=["tenant-mcp"])


@router.get("")
async def list_mcp_servers(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("mcp_server.view")),
):
    """List MCP servers in the current org."""
    return await tenant_mcp_svc.list_servers(db, cache, user.org_id)


@router.get("/available")
async def list_available_mcp_servers(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("mcp_server.view")),
):
    """List all available MCP servers: system + custom org servers."""
    return await tenant_mcp_svc.list_available(db, cache, user.org_id)


@router.post("", status_code=201)
async def create_mcp_server(
    data: McpServerCreate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("mcp_server.view")),
):
    """Create a custom MCP server in the org."""
    result = await tenant_mcp_svc.create_server(
        db, cache, user.org_id,
        data.codename, data.display_name, data.transport, data.connection_config,
    )
    await audit_svc.log_action(
        db, user.user_id, "create", "mcp_server", str(result.id),
        org_id=user.org_id, new_values=data.model_dump(),
    )
    return result


@router.put("/{server_id}")
async def update_mcp_server(
    server_id: str,
    data: McpServerUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("mcp_server.view")),
):
    """Update a custom MCP server."""
    result = await tenant_mcp_svc.update_server(
        db, cache, user.org_id, server_id,
        **data.model_dump(exclude_unset=True),
    )
    await audit_svc.log_action(
        db, user.user_id, "update", "mcp_server", server_id,
        org_id=user.org_id, new_values=data.model_dump(exclude_unset=True),
    )
    return result


@router.delete("/{server_id}", status_code=204)
async def delete_mcp_server(
    server_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("mcp_server.view")),
):
    """Delete a custom MCP server."""
    await tenant_mcp_svc.delete_server(db, cache, user.org_id, server_id)
    await audit_svc.log_action(
        db, user.user_id, "delete", "mcp_server", server_id, org_id=user.org_id,
    )


# ── Tool CRUD ────────────────────────────────────────────────────────────

@router.get("/{server_id}/tools")
async def list_tools(
    server_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("tool.view")),
):
    """List tools for a MCP server."""
    return await tenant_mcp_svc.list_tools(db, user.org_id, server_id)


@router.post("/{server_id}/tools", status_code=201)
async def create_tool(
    server_id: str,
    data: ToolCreate,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("mcp_server.view")),
):
    """Create a tool for a MCP server."""
    result = await tenant_mcp_svc.create_tool(
        db, user.org_id, server_id,
        data.codename, data.display_name, data.description, data.input_schema,
    )
    await audit_svc.log_action(
        db, user.user_id, "create", "tool", str(result.id),
        org_id=user.org_id, new_values={"server_id": server_id, **data.model_dump()},
    )
    return result


@router.delete("/{server_id}/tools/{tool_id}", status_code=204)
async def delete_tool(
    server_id: str,
    tool_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("mcp_server.view")),
):
    """Delete a tool from a MCP server."""
    await tenant_mcp_svc.delete_tool(db, user.org_id, server_id, tool_id)
    await audit_svc.log_action(
        db, user.user_id, "delete", "tool", tool_id,
        org_id=user.org_id, new_values={"server_id": server_id},
    )
