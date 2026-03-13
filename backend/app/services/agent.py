"""
System agent service — business logic for system-level agents.
Data rarely changes → cached in Redis with CACHE_AGENT_TTL.
"""
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.config.settings import settings
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation
from app.models.agent import CmsAgent, CmsOrgAgent
from app.models.mcp import CmsTool, CmsMcpServer
from app.models.organization import CmsOrganization
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AgentService:
    """System agent CRUD with Redis cache."""

    async def list_system(self, db: AsyncSession, cache: CacheService) -> list[dict]:
        """List all system agents (org_id IS NULL). Cached."""

        async def _fetch():
            result = await db.execute(
                select(CmsAgent).where(CmsAgent.org_id.is_(None)).order_by(CmsAgent.created_at.desc())
            )
            return [
                {
                    "id": str(a.id),
                    "codename": a.codename,
                    "display_name": a.display_name,
                    "description": a.description,
                    "default_config": a.default_config,
                    "is_active": a.is_active,
                    "is_public": a.is_public,
                    "org_id": None,
                    "created_at": a.created_at,
                }
                for a in result.scalars().all()
            ]

        return await cache.get_or_set(
            CacheKeys.system_agents(), _fetch, ttl=settings.CACHE_AGENT_TTL
        ) or []

    async def create(self, db: AsyncSession, cache: CacheService, **data) -> CmsAgent:
        """Create a system agent. Invalidates cache."""
        existing = await db.execute(
            select(CmsAgent).where(CmsAgent.codename == data["codename"], CmsAgent.org_id.is_(None))
        )
        if existing.scalar_one_or_none():
            raise CmsException(error_code=ErrorCode.AGENT_CODENAME_EXISTS, detail="Agent codename exists", status_code=409)

        agent = CmsAgent(org_id=None, **data)
        db.add(agent)
        await db.commit()
        await db.refresh(agent)

        await CacheInvalidation(cache).clear_system_agents()
        return agent

    async def get(self, db: AsyncSession, agent_id: str) -> CmsAgent:
        """Get a system agent (no cache for single item — list is cached)."""
        agent = await db.get(CmsAgent, agent_id)
        if not agent or agent.org_id is not None:
            raise CmsException(error_code=ErrorCode.AGENT_NOT_FOUND, detail="Agent not found", status_code=404)
        return agent

    async def update(self, db: AsyncSession, cache: CacheService, agent_id: str, **data) -> CmsAgent:
        """Update a system agent. Invalidates cache."""
        agent = await self.get(db, agent_id)
        for key, value in data.items():
            if value is not None:
                setattr(agent, key, value)
        await db.commit()
        await db.refresh(agent)

        await CacheInvalidation(cache).clear_system_agents()
        return agent

    async def delete(self, db: AsyncSession, cache: CacheService, agent_id: str) -> None:
        """Delete a system agent. Invalidates cache."""
        agent = await self.get(db, agent_id)
        await db.delete(agent)
        await db.commit()

        await CacheInvalidation(cache).clear_system_agents()

    # ── is_public toggle ─────────────────────────────────────────────────

    async def set_public(
        self, db: AsyncSession, cache: CacheService, agent_id: str, is_public: bool
    ) -> CmsAgent:
        """
        Toggle is_public on a system agent.
        - is_public=True: delete all CmsOrgAgent rows (agent available to ALL orgs)
        - is_public=False: just set the flag (no org assignments)
        Invalidates: sys:agents + org_agents:* for all affected orgs.
        """
        agent = await self.get(db, agent_id)
        inv = CacheInvalidation(cache)

        if is_public:
            result = await db.execute(
                select(CmsOrgAgent.org_id).where(CmsOrgAgent.agent_id == agent.id)
            )
            affected_org_ids = [str(r) for r in result.scalars().all()]

            await db.execute(
                delete(CmsOrgAgent).where(CmsOrgAgent.agent_id == agent.id)
            )
            agent.is_public = True

            # Invalidate cache for affected orgs
            for org_id in affected_org_ids:
                await inv.clear_org_agents(org_id)
        else:
            agent.is_public = False
            await inv.clear_all_org_agents_cache()

        await db.commit()
        await db.refresh(agent)
        await inv.clear_system_agents()
        return agent

    # ── Org assignment ────────────────────────────────────────────────────

    async def list_assigned_orgs(self, db: AsyncSession, agent_id: str) -> list[dict]:
        """List orgs assigned to this agent via CmsOrgAgent."""
        await self.get(db, agent_id)  # validate agent exists

        result = await db.execute(
            select(CmsOrgAgent, CmsOrganization.name)
            .join(CmsOrganization, CmsOrganization.id == CmsOrgAgent.org_id)
            .where(CmsOrgAgent.agent_id == agent_id)
        )
        return [
            {
                "org_id": str(row.CmsOrgAgent.org_id),
                "org_name": row.name,
                "is_enabled": row.CmsOrgAgent.is_enabled,
            }
            for row in result.all()
        ]

    async def set_assigned_orgs(
        self, db: AsyncSession, cache: CacheService, agent_id: str, org_ids: list[str]
    ) -> list[dict]:
        """
        Set org assignment for an agent. Diff current vs desired.
        Only works when is_public=False.
        """
        agent = await self.get(db, agent_id)
        if agent.is_public:
            raise CmsException(
                error_code=ErrorCode.AGENT_NOT_FOUND,
                detail="Cannot assign orgs to a public agent",
                status_code=400,
            )

        inv = CacheInvalidation(cache)

        # Current assignments
        result = await db.execute(
            select(CmsOrgAgent).where(CmsOrgAgent.agent_id == agent.id)
        )
        current = {str(oa.org_id): oa for oa in result.scalars().all()}
        desired = set(org_ids)
        current_ids = set(current.keys())

        # Add new assignments
        for oid in desired - current_ids:
            db.add(CmsOrgAgent(org_id=oid, agent_id=agent.id, is_enabled=True, is_public=False))
            await inv.clear_org_agents(oid)

        # Remove undesired assignments
        for oid in current_ids - desired:
            await db.delete(current[oid])
            await inv.clear_org_agents(oid)

        await db.commit()
        await inv.clear_system_agents()
        return await self.list_assigned_orgs(db, agent_id)

    # ── Agent tools ───────────────────────────────────────────────────────

    async def list_agent_tools(self, db: AsyncSession, agent_id: str) -> list[dict]:
        """
        List tools for a system agent based on AGENT_TOOLS mapping.
        Queries CmsTool + CmsMcpServer for display info.
        """
        from app.db_sync.tools import AGENT_TOOLS

        agent = await self.get(db, agent_id)
        tool_codenames = AGENT_TOOLS.get(agent.codename, [])

        if not tool_codenames:
            return []

        result = await db.execute(
            select(CmsTool, CmsMcpServer.display_name.label("server_name"))
            .join(CmsMcpServer, CmsMcpServer.id == CmsTool.mcp_server_id)
            .where(CmsTool.codename.in_(tool_codenames))
        )
        return [
            {
                "id": str(row.CmsTool.id),
                "codename": row.CmsTool.codename,
                "display_name": row.CmsTool.display_name,
                "description": row.CmsTool.description,
                "server_name": row.server_name,
            }
            for row in result.all()
        ]


# Singleton
agent_svc = AgentService()
