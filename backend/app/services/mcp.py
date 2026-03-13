"""
MCP service — CRUD for system-level MCP servers and tools.
Data rarely changes → cached in Redis with CACHE_DEFAULT_TTL.
"""
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.config.settings import settings
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation
from app.models.mcp import CmsMcpServer, CmsTool
from app.models.agent_access import CmsAgentMcpServer, CmsOrgMcpServer
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
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
                    "requires_env_vars": s.requires_env_vars,
                    "is_active": s.is_active,
                    "is_public": s.is_public,
                    "org_id": None,
                    "created_at": s.created_at,
                }
                for s in result.scalars().all()
            ]

        return await cache.get_or_set(
            CacheKeys.system_mcp_servers(), _fetch, ttl=settings.CACHE_DEFAULT_TTL
        ) or []

    async def create(self, db: AsyncSession, cache: CacheService, **data) -> CmsMcpServer:
        """Create or update a system MCP server (upsert). Invalidates cache."""
        result = await db.execute(
            select(CmsMcpServer).where(CmsMcpServer.codename == data["codename"], CmsMcpServer.org_id.is_(None))
        )
        server = result.scalar_one_or_none()

        if server:
            # Update existing
            for key, value in data.items():
                if key != "codename" and value is not None:
                    setattr(server, key, value)
        else:
            # Create new
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
        """Update a system MCP server. Handles is_public toggle. Invalidates cache."""
        server = await self.get(db, server_id)
        inv = CacheInvalidation(cache)

        # Detect is_public toggle: True → False = revoke all org assignments
        was_public = server.is_public
        new_public = data.get("is_public")

        for key, value in data.items():
            if value is not None:
                setattr(server, key, value)
        await db.commit()
        await db.refresh(server)

        await inv.clear_system_mcp_servers()

        if was_public and new_public is False:
            # Revoke all org assignments + invalidate
            await db.execute(
                sa_delete(CmsOrgMcpServer).where(CmsOrgMcpServer.mcp_server_id == server_id)
            )
            await db.commit()
            await inv.clear_all_org_mcp_cache()
            logger.info(f"MCP server {server_id} toggled to non-public: revoked all org assignments")

        return server

    async def delete(self, db: AsyncSession, cache: CacheService, server_id: str) -> None:
        """Delete a system MCP server. Cascade: remove all agent-MCP + org-MCP links. Invalidates cache."""
        server = await self.get(db, server_id)

        # Find affected org_ids + agent_ids BEFORE deleting for cache invalidation
        agent_links = await db.execute(
            select(CmsAgentMcpServer.agent_id, CmsAgentMcpServer.org_id)
            .where(CmsAgentMcpServer.mcp_server_id == server_id)
        )
        affected = agent_links.all()

        # Cascade delete agent-MCP links
        await db.execute(
            sa_delete(CmsAgentMcpServer).where(CmsAgentMcpServer.mcp_server_id == server_id)
        )
        # Cascade delete org-MCP links
        await db.execute(
            sa_delete(CmsOrgMcpServer).where(CmsOrgMcpServer.mcp_server_id == server_id)
        )

        await db.delete(server)
        await db.commit()

        # Invalidate caches
        inv = CacheInvalidation(cache)
        await inv.clear_system_mcp_servers()
        for row in affected:
            await inv.clear_agent_mcp_servers(str(row.agent_id), str(row.org_id))

    # ── Org Assignment ─────────────────────────────────────────────────

    async def list_assigned_orgs(
        self, db: AsyncSession, server_id: str,
    ) -> list[str]:
        """List org IDs that a system MCP server is assigned to."""
        result = await db.execute(
            select(CmsOrgMcpServer.org_id).where(CmsOrgMcpServer.mcp_server_id == server_id)
        )
        return [str(oid) for oid in result.scalars().all()]

    async def assign_to_orgs(
        self, db: AsyncSession, cache: CacheService, server_id: str, org_ids: list[str],
    ) -> list[str]:
        """Assign a system MCP server to given orgs (skip duplicates). Returns assigned org_ids."""
        existing = await db.execute(
            select(CmsOrgMcpServer.org_id).where(CmsOrgMcpServer.mcp_server_id == server_id)
        )
        existing_ids = {str(oid) for oid in existing.scalars().all()}

        added = []
        for oid in org_ids:
            if oid not in existing_ids:
                db.add(CmsOrgMcpServer(org_id=oid, mcp_server_id=server_id))
                added.append(oid)

        if added:
            await db.commit()

        logger.info(f"Assigned MCP {server_id} to {len(added)} orgs")
        return added

    async def unassign_from_org(
        self, db: AsyncSession, cache: CacheService, server_id: str, org_id: str,
    ) -> None:
        """Unassign a system MCP server from an org."""
        await db.execute(
            sa_delete(CmsOrgMcpServer).where(
                CmsOrgMcpServer.mcp_server_id == server_id,
                CmsOrgMcpServer.org_id == org_id,
            )
        )
        await db.commit()
        logger.info(f"Unassigned MCP {server_id} from org {org_id}")

    async def set_assigned_orgs(
        self, db: AsyncSession, cache: CacheService, server_id: str, org_ids: list[str],
    ) -> list[str]:
        """Set the exact list of assigned orgs for a system MCP server (add missing, remove extras)."""
        # Block org assignment for public servers
        server = await self.get(db, server_id)
        if server.is_public:
            raise CmsException(
                error_code=ErrorCode.MCP_NOT_FOUND,
                detail="Cannot assign orgs to a public MCP server",
                status_code=400,
            )

        existing = await db.execute(
            select(CmsOrgMcpServer.org_id).where(CmsOrgMcpServer.mcp_server_id == server_id)
        )
        existing_ids = {str(oid) for oid in existing.scalars().all()}
        target_ids = set(org_ids)

        # Remove orgs no longer assigned
        to_remove = existing_ids - target_ids
        if to_remove:
            await db.execute(
                sa_delete(CmsOrgMcpServer).where(
                    CmsOrgMcpServer.mcp_server_id == server_id,
                    CmsOrgMcpServer.org_id.in_(to_remove),
                )
            )

        # Add new org assignments
        to_add = target_ids - existing_ids
        for oid in to_add:
            db.add(CmsOrgMcpServer(org_id=oid, mcp_server_id=server_id))

        if to_remove or to_add:
            await db.commit()

        logger.info(f"Set MCP {server_id} to {len(target_ids)} orgs (added {len(to_add)}, removed {len(to_remove)})")
        return list(target_ids)

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

    # ── Tool Discovery ────────────────────────────────────────────────

    async def discover_tools(self, mcp_config: dict) -> list[dict]:
        """
        Parse MCP JSON config, connect to each server via stdio,
        list tools and return metadata for saving to DB.

        Args:
            mcp_config: Standard MCP config: {"mcpServers": {"name": {...}}}

        Returns:
            List of {server_name, tools: [{name, description, inputSchema}], error?}
        """
        servers = mcp_config.get("mcpServers", {})
        if not servers:
            return []

        results = []

        for server_name, cfg in servers.items():
            try:
                command = cfg.get("command")
                args = list(cfg.get("args", []))
                env = dict(cfg.get("env") or {})

                if not command:
                    results.append({
                        "server_name": server_name,
                        "tools": [],
                        "error": "Missing 'command' in config",
                    })
                    continue

                logger.info(f"Connecting to MCP server '{server_name}': {command} {' '.join(args)}")

                server_params = StdioServerParameters(
                    command=command,
                    args=args,
                    env=env if env else None,
                )

                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools_result = await session.list_tools()

                        tools = [
                            {
                                "name": tool.name,
                                "description": tool.description or "",
                                "input_schema": tool.inputSchema if hasattr(tool, "inputSchema") else {},
                            }
                            for tool in tools_result.tools
                        ]

                        results.append({
                            "server_name": server_name,
                            "tools": tools,
                            "error": None,
                        })
                        logger.info(
                            f"Discovered {len(tools)} tools from '{server_name}'"
                        )

            except Exception as e:
                logger.error(f"Failed to discover tools from '{server_name}': {e}")
                results.append({
                    "server_name": server_name,
                    "tools": [],
                    "error": str(e),
                })

        return results

    async def sync_discovered_tools(
        self, db: AsyncSession, cache: CacheService, server_id: str, mcp_config: dict
    ) -> list[dict]:
        """
        Discover tools from MCP config and sync them to a server in DB.
        Creates new tools, updates existing ones.
        """
        discovered = await self.discover_tools(mcp_config)

        synced_tools = []
        for result in discovered:
            if result.get("error"):
                continue

            for tool_info in result.get("tools", []):
                tool_name = tool_info["name"]
                # Check if tool already exists
                existing = await db.execute(
                    select(CmsTool).where(
                        CmsTool.mcp_server_id == server_id,
                        CmsTool.codename == tool_name,
                    )
                )
                tool = existing.scalar_one_or_none()

                if not tool:
                    tool = CmsTool(
                        mcp_server_id=server_id,
                        codename=tool_name,
                        display_name=tool_name.replace("_", " ").title(),
                        description=tool_info.get("description"),
                        input_schema=tool_info.get("input_schema"),
                        is_active=True,
                    )
                    db.add(tool)
                    logger.info(f"  + Tool synced: {tool_name}")
                else:
                    tool.description = tool_info.get("description")
                    tool.input_schema = tool_info.get("input_schema")
                    logger.info(f"  ~ Tool updated: {tool_name}")

                synced_tools.append(tool_info)

        await db.commit()
        await CacheInvalidation(cache).clear_system_mcp_servers()
        logger.info(f"Synced {len(synced_tools)} tools to server {server_id}")
        return discovered


# Singleton
mcp_svc = McpService()
