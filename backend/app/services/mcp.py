"""
MCP service — CRUD for system-level MCP servers and tools.
Data rarely changes → cached in Redis with CACHE_DEFAULT_TTL.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.config.settings import settings
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation
from app.models.mcp import CmsMcpServer, CmsTool
from app.utils.logging import get_logger

logger = get_logger(__name__)


class McpService:
    """System MCP server + tool CRUD with Redis cache."""

    async def list_system(self, db: AsyncSession, cache: CacheService) -> list[dict]:
        """List all system MCP servers. Cached."""

        async def _fetch():
            result = await db.execute(
                select(CmsMcpServer).where(CmsMcpServer.org_id.is_(None)).order_by(CmsMcpServer.created_at.desc())
            )
            return [
                {
                    "id": str(s.id),
                    "codename": s.codename,
                    "display_name": s.display_name,
                    "transport": s.transport,
                    "connection_config": s.connection_config,
                    "is_active": s.is_active,
                    "org_id": None,
                    "created_at": s.created_at,
                }
                for s in result.scalars().all()
            ]

        return await cache.get_or_set(
            CacheKeys.system_mcp_servers(), _fetch, ttl=settings.CACHE_DEFAULT_TTL
        ) or []

    async def create(self, db: AsyncSession, cache: CacheService, **data) -> CmsMcpServer:
        """Create a system MCP server. Invalidates cache."""
        existing = await db.execute(
            select(CmsMcpServer).where(CmsMcpServer.codename == data["codename"], CmsMcpServer.org_id.is_(None))
        )
        if existing.scalar_one_or_none():
            raise CmsException(error_code=ErrorCode.MCP_CODENAME_EXISTS, detail="MCP codename exists", status_code=409)

        server = CmsMcpServer(org_id=None, is_active=True, **data)
        db.add(server)
        await db.commit()
        await db.refresh(server)

        await CacheInvalidation(cache).clear_system_mcp_servers()
        return server

    async def get(self, db: AsyncSession, server_id: str) -> CmsMcpServer:
        """Get a system MCP server."""
        server = await db.get(CmsMcpServer, server_id)
        if not server or server.org_id is not None:
            raise CmsException(error_code=ErrorCode.MCP_NOT_FOUND, detail="MCP server not found", status_code=404)
        return server

    async def update(self, db: AsyncSession, cache: CacheService, server_id: str, **data) -> CmsMcpServer:
        """Update a system MCP server. Invalidates cache."""
        server = await self.get(db, server_id)
        for key, value in data.items():
            if value is not None:
                setattr(server, key, value)
        await db.commit()
        await db.refresh(server)

        await CacheInvalidation(cache).clear_system_mcp_servers()
        return server

    async def delete(self, db: AsyncSession, cache: CacheService, server_id: str) -> None:
        """Delete a system MCP server. Invalidates cache."""
        server = await self.get(db, server_id)
        await db.delete(server)
        await db.commit()

        await CacheInvalidation(cache).clear_system_mcp_servers()

    # ── Tools ─────────────────────────────────────────────────────────

    async def list_tools(self, db: AsyncSession, server_id: str) -> list[dict]:
        """List tools for a MCP server."""
        result = await db.execute(
            select(CmsTool).where(CmsTool.mcp_server_id == server_id).order_by(CmsTool.created_at.desc())
        )
        return [
            {
                "id": str(t.id),
                "mcp_server_id": str(t.mcp_server_id),
                "codename": t.codename,
                "display_name": t.display_name,
                "description": t.description,
                "input_schema": t.input_schema,
                "is_active": t.is_active,
                "created_at": t.created_at,
            }
            for t in result.scalars().all()
        ]

    async def create_tool(self, db: AsyncSession, cache: CacheService, server_id: str, **data) -> CmsTool:
        """Create a tool for a MCP server."""
        await self.get(db, server_id)  # validates server exists
        tool = CmsTool(mcp_server_id=server_id, is_active=True, **data)
        db.add(tool)
        await db.commit()
        await db.refresh(tool)

        # Invalidate MCP cache (tools are part of server listing)
        await CacheInvalidation(cache).clear_system_mcp_servers()
        return tool


# Singleton
mcp_svc = McpService()
