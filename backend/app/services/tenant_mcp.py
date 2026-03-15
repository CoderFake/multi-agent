"""
Tenant MCP service — custom MCP server + tool CRUD within an org.
Uses CacheInvalidation on mutation.
"""
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.cache.service import CacheService
from app.cache.keys import CacheKeys
from app.config.settings import settings
from app.models.mcp import CmsMcpServer, CmsTool
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TenantMcpService:
    """MCP server + tool management within an org."""

    async def list_servers(self, db: AsyncSession, cache: CacheService, org_id: str) -> list[dict]:
        """List MCP servers in the org. Cached."""

        async def _fetch():
            result = await db.execute(
                select(CmsMcpServer).where(CmsMcpServer.org_id == org_id)
            )
            return [
                {
                    "id": str(s.id), "codename": s.codename,
                    "display_name": s.display_name,
                    "transport": s.transport, "connection_config": s.connection_config,
                    "is_active": s.is_active,
                }
                for s in result.scalars().all()
            ]

        return await cache.get_or_set(
            CacheKeys.org_mcp(org_id), _fetch, ttl=settings.CACHE_DEFAULT_TTL,
        ) or []

    async def list_available(self, db: AsyncSession, cache: CacheService, org_id: str) -> list[dict]:
        """List all available MCP servers: system (org_id IS NULL) + custom org servers. Cached."""

        async def _fetch():
            result = await db.execute(
                select(CmsMcpServer).where(
                    or_(CmsMcpServer.org_id.is_(None), CmsMcpServer.org_id == org_id)
                )
            )
            return [
                {
                    "id": str(s.id), "codename": s.codename,
                    "display_name": s.display_name,
                    "transport": s.transport,
                    "requires_env_vars": s.requires_env_vars,
                    "is_system": s.org_id is None,
                    "is_active": s.is_active,
                }
                for s in result.scalars().all()
            ]

        return await cache.get_or_set(
            CacheKeys.org_mcp_available(org_id), _fetch, ttl=settings.CACHE_DEFAULT_TTL,
        ) or []

    async def create_server(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, codename: str, display_name: str,
        transport: str = "stdio", connection_config: dict = None,
        description: str = None,
    ) -> dict:
        """Create a custom MCP server in the org."""
        server = CmsMcpServer(
            org_id=org_id,
            codename=codename,
            display_name=display_name,
            transport=transport,
            connection_config=connection_config,
            is_active=True,
        )
        db.add(server)
        await db.commit()
        await db.refresh(server)

        logger.info(f"MCP server created: {server.codename} in org {org_id}")

        # Invalidate mcp list cache
        await cache.delete(CacheKeys.org_mcp(org_id))
        await cache.delete(CacheKeys.org_mcp_available(org_id))

        return {
            "id": str(server.id), "codename": server.codename,
            "display_name": server.display_name,
            "transport": server.transport, "connection_config": server.connection_config,
            "is_active": server.is_active,
        }

    async def update_server(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, server_id: str, **kwargs,
    ) -> dict:
        """Update a custom MCP server."""
        server = await self._get_server(db, org_id, server_id)

        for key, value in kwargs.items():
            if value is not None and hasattr(server, key):
                setattr(server, key, value)
        await db.commit()
        await db.refresh(server)

        # Invalidate mcp list cache
        await cache.delete(CacheKeys.org_mcp(org_id))
        await cache.delete(CacheKeys.org_mcp_available(org_id))

        return {
            "id": str(server.id), "codename": server.codename,
            "display_name": server.display_name,
            "transport": server.transport, "connection_config": server.connection_config,
            "is_active": server.is_active,
        }

    async def delete_server(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, server_id: str,
    ) -> None:
        """Delete a custom MCP server."""
        server = await self._get_server(db, org_id, server_id)
        await db.delete(server)
        await db.commit()

        # Invalidate mcp list cache
        await cache.delete(CacheKeys.org_mcp(org_id))
        await cache.delete(CacheKeys.org_mcp_available(org_id))

        logger.info(f"MCP server deleted: {server.codename} in org {org_id}")

    # ── Tool CRUD ────────────────────────────────────────────────────────

    async def list_tools(self, db: AsyncSession, org_id: str, server_id: str) -> list[dict]:
        """List tools for a MCP server (system or custom in this org)."""
        result = await db.execute(
            select(CmsMcpServer).where(
                CmsMcpServer.id == server_id,
                or_(CmsMcpServer.org_id.is_(None), CmsMcpServer.org_id == org_id),
            )
        )
        server = result.scalar_one_or_none()
        if not server:
            raise CmsException(error_code=ErrorCode.MCP_NOT_FOUND, detail="MCP server not found", status_code=404)

        tools_result = await db.execute(
            select(CmsTool).where(CmsTool.mcp_server_id == server_id)
        )
        return [
            {
                "id": str(t.id), "codename": t.codename,
                "display_name": t.display_name, "description": t.description,
                "input_schema": t.input_schema, "is_active": t.is_active,
            }
            for t in tools_result.scalars().all()
        ]

    async def create_tool(
        self, db: AsyncSession, org_id: str, server_id: str,
        codename: str, display_name: str,
        description: str = None, input_schema: dict = None,
    ) -> dict:
        """Create a tool for a MCP server."""
        await self._get_server(db, org_id, server_id)

        tool = CmsTool(
            mcp_server_id=server_id,
            codename=codename,
            display_name=display_name,
            description=description,
            input_schema=input_schema,
            is_active=True,
        )
        db.add(tool)
        await db.commit()
        await db.refresh(tool)

        return {
            "id": str(tool.id), "codename": tool.codename,
            "display_name": tool.display_name, "description": tool.description,
            "input_schema": tool.input_schema, "is_active": tool.is_active,
        }

    async def delete_tool(
        self, db: AsyncSession, org_id: str,
        server_id: str, tool_id: str,
    ) -> None:
        """Delete a tool from a MCP server."""
        await self._get_server(db, org_id, server_id)

        result = await db.execute(
            select(CmsTool).where(CmsTool.id == tool_id, CmsTool.mcp_server_id == server_id)
        )
        tool = result.scalar_one_or_none()
        if not tool:
            raise CmsException(error_code=ErrorCode.MCP_NOT_FOUND, detail="Tool not found", status_code=404)

        await db.delete(tool)
        await db.commit()

    # ── Internal ─────────────────────────────────────────────────────────

    async def _get_server(self, db: AsyncSession, org_id: str, server_id: str) -> CmsMcpServer:
        """Get MCP server by ID within org. Raises 404 if not found."""
        result = await db.execute(
            select(CmsMcpServer).where(CmsMcpServer.id == server_id, CmsMcpServer.org_id == org_id)
        )
        server = result.scalar_one_or_none()
        if not server:
            raise CmsException(error_code=ErrorCode.MCP_NOT_FOUND, detail="MCP server not found", status_code=404)
        return server


# Singleton
tenant_mcp_svc = TenantMcpService()
