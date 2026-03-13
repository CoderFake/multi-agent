"""
Tenant Agent Access Control service.
Manages: Agent ↔ MCP, Group ↔ Agent, Group ↔ Tool access.
Uses Redis → DB pattern with cache invalidation on mutations.
"""
from datetime import datetime, timezone

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation
from app.config.settings import settings
from app.models.agent import CmsOrgAgent
from app.models.mcp import CmsMcpServer, CmsTool
from app.models.agent import CmsAgent
from app.models.agent_access import CmsAgentMcpServer, CmsGroupAgent, CmsGroupToolAccess, CmsOrgMcpServer
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TenantAgentAccessService:
    """Agent access control within an org."""

    # ── Available MCP Servers for org ────────────────────────────────────

    async def list_available_mcp_servers(
        self, db: AsyncSession, org_id: str,
    ) -> list[dict]:
        """List MCP servers available to this org: public system servers + explicitly assigned."""
        result = await db.execute(
            select(CmsMcpServer).where(
                CmsMcpServer.org_id.is_(None),  # system servers only
                CmsMcpServer.is_active == True,
                or_(
                    CmsMcpServer.is_public == True,
                    CmsMcpServer.id.in_(
                        select(CmsOrgMcpServer.mcp_server_id).where(
                            CmsOrgMcpServer.org_id == org_id
                        )
                    ),
                ),
            )
        )
        return [
            {
                "id": str(s.id),
                "codename": s.codename,
                "display_name": s.display_name,
                "transport": s.transport,
                "requires_env_vars": s.requires_env_vars,
            }
            for s in result.scalars().all()
        ]

    async def list_agent_mcp_servers(
        self, db: AsyncSession, cache: CacheService, org_id: str, agent_id: str,
    ) -> list[dict]:
        """List MCP servers assigned to an agent. Cached."""
        cache_key = CacheKeys.agent_mcp_servers(agent_id, org_id)

        async def _fetch():
            result = await db.execute(
                select(CmsAgentMcpServer, CmsMcpServer)
                .join(CmsMcpServer, CmsAgentMcpServer.mcp_server_id == CmsMcpServer.id)
                .where(
                    CmsAgentMcpServer.org_id == org_id,
                    CmsAgentMcpServer.agent_id == agent_id,
                )
            )
            return [
                {
                    "id": str(row.CmsAgentMcpServer.id),
                    "agent_id": str(row.CmsAgentMcpServer.agent_id),
                    "mcp_server_id": str(row.CmsAgentMcpServer.mcp_server_id),
                    "mcp_server_codename": row.CmsMcpServer.codename,
                    "mcp_server_name": row.CmsMcpServer.display_name,
                    "is_active": row.CmsAgentMcpServer.is_active,
                    "env_overrides": row.CmsAgentMcpServer.env_overrides,
                    "requires_env_vars": row.CmsMcpServer.requires_env_vars,
                    "connection_config": row.CmsMcpServer.connection_config,
                }
                for row in result.all()
            ]

        return await cache.get_or_set(cache_key, _fetch, ttl=settings.CACHE_DEFAULT_TTL) or []

    async def assign_mcp_to_agent(
        self, db: AsyncSession, cache: CacheService, org_id: str,
        agent_id: str, mcp_server_id: str, env_overrides: dict | None = None,
    ) -> dict:
        """Assign an MCP server to an agent."""
        # Check not already assigned
        existing = await db.execute(
            select(CmsAgentMcpServer).where(
                CmsAgentMcpServer.org_id == org_id,
                CmsAgentMcpServer.agent_id == agent_id,
                CmsAgentMcpServer.mcp_server_id == mcp_server_id,
            )
        )
        if existing.scalar_one_or_none():
            raise CmsException(
                error_code=ErrorCode.VALIDATION_ERROR,
                detail="MCP server already assigned to this agent",
                status_code=409,
            )

        link = CmsAgentMcpServer(
            org_id=org_id, agent_id=agent_id,
            mcp_server_id=mcp_server_id, is_active=True,
            env_overrides=env_overrides,
            created_at=datetime.now(timezone.utc),
        )
        db.add(link)
        await db.commit()
        await db.refresh(link)

        # Invalidate
        inv = CacheInvalidation(cache)
        await inv.clear_agent_mcp_servers(agent_id, org_id)

        logger.info(f"Assigned MCP {mcp_server_id} to agent {agent_id} in org {org_id}")
        return {"id": str(link.id), "agent_id": agent_id, "mcp_server_id": mcp_server_id, "is_active": True}

    async def revoke_mcp_from_agent(
        self, db: AsyncSession, cache: CacheService, org_id: str,
        agent_id: str, mcp_server_id: str,
    ) -> None:
        """Revoke an MCP server from an agent."""
        result = await db.execute(
            select(CmsAgentMcpServer).where(
                CmsAgentMcpServer.org_id == org_id,
                CmsAgentMcpServer.agent_id == agent_id,
                CmsAgentMcpServer.mcp_server_id == mcp_server_id,
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            raise CmsException(error_code=ErrorCode.AGENT_NOT_FOUND, detail="MCP link not found", status_code=404)

        await db.delete(link)
        await db.commit()

        # Invalidate
        inv = CacheInvalidation(cache)
        await inv.clear_agent_mcp_servers(agent_id, org_id)

        logger.info(f"Revoked MCP {mcp_server_id} from agent {agent_id} in org {org_id}")

    async def update_agent_mcp_env(
        self, db: AsyncSession, cache: CacheService, org_id: str,
        agent_id: str, mcp_server_id: str, env_overrides: dict,
    ) -> dict:
        """Update env_overrides for an agent-MCP link."""
        result = await db.execute(
            select(CmsAgentMcpServer).where(
                CmsAgentMcpServer.org_id == org_id,
                CmsAgentMcpServer.agent_id == agent_id,
                CmsAgentMcpServer.mcp_server_id == mcp_server_id,
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            raise CmsException(error_code=ErrorCode.AGENT_NOT_FOUND, detail="MCP link not found", status_code=404)

        link.env_overrides = env_overrides
        await db.commit()
        await db.refresh(link)

        # Invalidate
        inv = CacheInvalidation(cache)
        await inv.clear_agent_mcp_servers(agent_id, org_id)

        logger.info(f"Updated env_overrides for MCP {mcp_server_id} on agent {agent_id}")
        return {
            "id": str(link.id), "agent_id": agent_id,
            "mcp_server_id": mcp_server_id, "env_overrides": link.env_overrides,
            "is_active": link.is_active,
        }

    # ── Group ↔ Agent ────────────────────────────────────────────────────

    async def list_group_agents(
        self, db: AsyncSession, cache: CacheService, org_id: str, group_id: str,
    ) -> list[dict]:
        """List agents assigned to a group. Cached."""
        cache_key = CacheKeys.group_agents(group_id, org_id)

        async def _fetch():
            result = await db.execute(
                select(CmsGroupAgent, CmsAgent)
                .join(CmsAgent, CmsGroupAgent.agent_id == CmsAgent.id)
                .where(
                    CmsGroupAgent.org_id == org_id,
                    CmsGroupAgent.group_id == group_id,
                )
            )
            return [
                {
                    "id": str(row.CmsGroupAgent.id),
                    "group_id": str(row.CmsGroupAgent.group_id),
                    "agent_id": str(row.CmsGroupAgent.agent_id),
                    "agent_codename": row.CmsAgent.codename,
                    "agent_name": row.CmsAgent.display_name,
                }
                for row in result.all()
            ]

        return await cache.get_or_set(cache_key, _fetch, ttl=settings.CACHE_DEFAULT_TTL) or []

    async def assign_agents_to_group(
        self, db: AsyncSession, cache: CacheService, org_id: str,
        group_id: str, agent_ids: list[str],
    ) -> list[dict]:
        """Assign agents to a group (skip duplicates)."""
        # Get existing
        existing = await db.execute(
            select(CmsGroupAgent.agent_id).where(
                CmsGroupAgent.org_id == org_id,
                CmsGroupAgent.group_id == group_id,
            )
        )
        existing_ids = {str(r) for r in existing.scalars().all()}

        new_links = []
        for aid in agent_ids:
            if aid not in existing_ids:
                link = CmsGroupAgent(
                    group_id=group_id, agent_id=aid, org_id=org_id,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(link)
                new_links.append(link)

        if new_links:
            await db.commit()

        # Invalidate
        inv = CacheInvalidation(cache)
        await inv.clear_group_agents(group_id, org_id)

        logger.info(f"Assigned {len(new_links)} agents to group {group_id} in org {org_id}")
        return [
            {"id": str(l.id), "group_id": group_id, "agent_id": str(l.agent_id)}
            for l in new_links
        ]

    async def revoke_agent_from_group(
        self, db: AsyncSession, cache: CacheService, org_id: str,
        group_id: str, agent_id: str,
    ) -> None:
        """Remove agent access from a group."""
        result = await db.execute(
            select(CmsGroupAgent).where(
                CmsGroupAgent.org_id == org_id,
                CmsGroupAgent.group_id == group_id,
                CmsGroupAgent.agent_id == agent_id,
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            raise CmsException(error_code=ErrorCode.AGENT_NOT_FOUND, detail="Group-agent link not found", status_code=404)

        await db.delete(link)
        await db.commit()

        # Invalidate
        inv = CacheInvalidation(cache)
        await inv.clear_group_agents(group_id, org_id)

        logger.info(f"Revoked agent {agent_id} from group {group_id}")

    # ── Group ↔ Tool Access ─────────────────────────────────────────────

    async def list_group_tool_access(
        self, db: AsyncSession, cache: CacheService, org_id: str, group_id: str,
    ) -> list[dict]:
        """List tool access settings for a group. Cached."""
        cache_key = CacheKeys.group_tools(group_id, org_id)

        async def _fetch():
            result = await db.execute(
                select(CmsGroupToolAccess, CmsTool)
                .join(CmsTool, CmsGroupToolAccess.tool_id == CmsTool.id)
                .where(
                    CmsGroupToolAccess.org_id == org_id,
                    CmsGroupToolAccess.group_id == group_id,
                )
            )
            return [
                {
                    "id": str(row.CmsGroupToolAccess.id),
                    "group_id": str(row.CmsGroupToolAccess.group_id),
                    "tool_id": str(row.CmsGroupToolAccess.tool_id),
                    "tool_codename": row.CmsTool.codename,
                    "tool_name": row.CmsTool.display_name,
                    "is_enabled": row.CmsGroupToolAccess.is_enabled,
                }
                for row in result.all()
            ]

        return await cache.get_or_set(cache_key, _fetch, ttl=settings.CACHE_DEFAULT_TTL) or []

    async def toggle_tool_access(
        self, db: AsyncSession, cache: CacheService, org_id: str,
        group_id: str, tool_id: str, is_enabled: bool,
    ) -> dict:
        """Toggle a tool's access for a group. Creates record if not exists."""
        result = await db.execute(
            select(CmsGroupToolAccess).where(
                CmsGroupToolAccess.org_id == org_id,
                CmsGroupToolAccess.group_id == group_id,
                CmsGroupToolAccess.tool_id == tool_id,
            )
        )
        access = result.scalar_one_or_none()

        if access:
            access.is_enabled = is_enabled
        else:
            access = CmsGroupToolAccess(
                group_id=group_id, tool_id=tool_id, org_id=org_id,
                is_enabled=is_enabled,
                created_at=datetime.now(timezone.utc),
            )
            db.add(access)

        await db.commit()
        await db.refresh(access)

        # Invalidate
        inv = CacheInvalidation(cache)
        await inv.clear_group_tools(group_id, org_id)

        return {
            "id": str(access.id), "group_id": group_id,
            "tool_id": tool_id, "is_enabled": access.is_enabled,
        }

    async def bulk_toggle_tools(
        self, db: AsyncSession, cache: CacheService, org_id: str,
        group_id: str, entries: list[dict],
    ) -> list[dict]:
        """Bulk toggle tool access for a group."""
        results = []
        for entry in entries:
            r = await self.toggle_tool_access(
                db, cache, org_id, group_id, entry["tool_id"], entry["is_enabled"],
            )
            results.append(r)
        return results

    # ── Org Agent is_public toggle ───────────────────────────────────────

    async def toggle_agent_public(
        self, db: AsyncSession, cache: CacheService, org_id: str,
        agent_id: str, is_public: bool,
    ) -> dict:
        """Toggle is_public flag for an org agent. Auto-creates CmsOrgAgent if missing."""
        result = await db.execute(
            select(CmsOrgAgent).where(
                CmsOrgAgent.org_id == org_id,
                CmsOrgAgent.agent_id == agent_id,
            )
        )
        org_agent = result.scalar_one_or_none()

        if not org_agent:
            # Auto-create for custom agents that lack CmsOrgAgent row
            org_agent = CmsOrgAgent(
                org_id=org_id, agent_id=agent_id,
                is_enabled=True, is_public=is_public,
            )
            db.add(org_agent)
        else:
            org_agent.is_public = is_public

        await db.commit()

        # Invalidate: agent list + all user access caches
        inv = CacheInvalidation(cache)
        await inv.clear_org_agents(org_id)
        await inv.clear_all_access_control(org_id)

        logger.info(f"Agent {agent_id} is_public={is_public} in org {org_id}")
        return {"agent_id": agent_id, "is_public": is_public}


# Singleton
tenant_agent_access_svc = TenantAgentAccessService()
