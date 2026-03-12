"""
System agent service — business logic for system-level agents.
Data rarely changes → cached in Redis with CACHE_AGENT_TTL.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.config.settings import settings
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation
from app.models.agent import CmsAgent
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

        # Invalidate list cache
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


# Singleton
agent_svc = AgentService()
