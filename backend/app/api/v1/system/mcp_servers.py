"""
System API — MCP Server + Tool CRUD (superuser only).
Thin router — all logic in mcp_svc.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_superuser
from app.common.types import CurrentUser
from app.schemas.mcp import McpServerCreate, McpServerUpdate, McpServerResponse, ToolCreate, ToolResponse
from app.schemas.common import SuccessResponse
from app.cache.service import CacheService
from app.services.mcp import mcp_svc
from app.services.audit import audit_svc

router = APIRouter(prefix="/mcp-servers", tags=["system-mcp"])


@router.get("", response_model=list[McpServerResponse])
async def list_mcp_servers(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """List all system MCP servers."""
    return await mcp_svc.list_system(db, cache)


@router.post("", response_model=McpServerResponse, status_code=201)
async def create_mcp_server(
    data: McpServerCreate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Create a system MCP server."""
    server = await mcp_svc.create(db, cache, **data.model_dump())
    await audit_svc.log_action(db, user.user_id, "create", "mcp_server", str(server.id), new_values=data.model_dump())
    return server


@router.put("/{server_id}", response_model=McpServerResponse)
async def update_mcp_server(
    server_id: str,
    data: McpServerUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Update a system MCP server."""
    server = await mcp_svc.update(db, cache, server_id, **data.model_dump(exclude_unset=True))
    await audit_svc.log_action(db, user.user_id, "update", "mcp_server", str(server.id), new_values=data.model_dump(exclude_unset=True))
    return server


@router.delete("/{server_id}", response_model=SuccessResponse)
async def delete_mcp_server(
    server_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Delete a system MCP server."""
    await mcp_svc.delete(db, cache, server_id)
    await audit_svc.log_action(db, user.user_id, "delete", "mcp_server", server_id)
    return {"message": "MCP server deleted successfully"}


# ── Tools ─────────────────────────────────────────────────────────────────

@router.get("/{server_id}/tools", response_model=list[ToolResponse])
async def list_tools(
    server_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_superuser),
):
    """List tools for a MCP server."""
    return await mcp_svc.list_tools(db, server_id)


@router.post("/{server_id}/tools", response_model=ToolResponse, status_code=201)
async def create_tool(
    server_id: str,
    data: ToolCreate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Create a tool for a MCP server."""
    tool = await mcp_svc.create_tool(db, cache, server_id, **data.model_dump())
    return tool
