"""
Tenant agent service — custom agent CRUD + system agent enable/disable.
Uses CacheService.get_or_set() for reads + CacheInvalidation on mutation.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.config.settings import settings
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation
from app.models.agent import CmsAgent, CmsOrgAgent
from app.utils.logging import get_logger
from app.utils import datetime_utils

logger = get_logger(__name__)


class TenantAgentService:
    """Agent management within an org — custom CRUD + system enable/disable."""

    async def list_agents(self, db: AsyncSession, cache: CacheService, org_id: str) -> list[dict]:
        """List available agents: system enabled + org custom agents. Cached."""

        async def _fetch():
            result = await db.execute(
                select(CmsAgent, CmsOrgAgent)
                .outerjoin(CmsOrgAgent, (CmsOrgAgent.agent_id == CmsAgent.id) & (CmsOrgAgent.org_id == org_id))
                .where(CmsAgent.org_id.is_(None), CmsAgent.is_active.is_(True))
            )
            system_agents = [
                {
                    "id": str(agent.id),
                    "codename": agent.codename,
                    "display_name": agent.display_name,
                    "description": agent.description,
                    "is_active": agent.is_active,
                    "is_system": True,
                    "is_enabled": org_agent.is_enabled if org_agent else False,
                    "is_public": org_agent.is_public if org_agent else False,
                    "config_override": org_agent.config_override if org_agent else None,
                }
                for agent, org_agent in result.all()
            ]

            # Custom org agents (left join CmsOrgAgent for is_public)
            result = await db.execute(
                select(CmsAgent, CmsOrgAgent)
                .outerjoin(CmsOrgAgent, (CmsOrgAgent.agent_id == CmsAgent.id) & (CmsOrgAgent.org_id == org_id))
                .where(CmsAgent.org_id == org_id)
            )
            custom_agents = [
                {
                    "id": str(agent.id),
                    "codename": agent.codename,
                    "display_name": agent.display_name,
                    "description": agent.description,
                    "is_active": agent.is_active,
                    "is_system": False,
                    "is_enabled": agent.is_active,
                    "is_public": org_agent.is_public if org_agent else False,
                    "config_override": agent.default_config,
                }
                for agent, org_agent in result.all()
            ]
            return system_agents + custom_agents

        return await cache.get_or_set(
            CacheKeys.org_agents(org_id), _fetch, ttl=settings.CACHE_AGENT_TTL,
        ) or []

    async def create_agent(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, codename: str, display_name: str,
        description: str = None, default_config: dict = None,
    ) -> dict:
        """Create a custom agent. Invalidates org agents + system agents cache."""
        agent = CmsAgent(
            org_id=org_id,
            codename=codename,
            display_name=display_name,
            description=description,
            default_config=default_config,
            is_active=True,
            created_at=datetime_utils.now(),
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)

        inv = CacheInvalidation(cache)
        await inv.clear_org_agents(org_id)

        logger.info(f"Custom agent created: {agent.codename} in org {org_id}")
        return {
            "id": str(agent.id), "codename": agent.codename,
            "display_name": agent.display_name, "description": agent.description,
            "is_active": agent.is_active, "is_system": False,
        }

    async def update_agent(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, agent_id: str, **kwargs,
    ) -> dict:
        """Update a custom agent. Invalidates org agents cache."""
        result = await db.execute(
            select(CmsAgent).where(CmsAgent.id == agent_id, CmsAgent.org_id == org_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise CmsException(error_code=ErrorCode.AGENT_NOT_FOUND, detail="Agent not found", status_code=404)

        for key, value in kwargs.items():
            if value is not None and hasattr(agent, key):
                setattr(agent, key, value)
        await db.commit()
        await db.refresh(agent)

        inv = CacheInvalidation(cache)
        await inv.clear_org_agents(org_id)

        return {
            "id": str(agent.id), "codename": agent.codename,
            "display_name": agent.display_name, "description": agent.description,
            "is_active": agent.is_active, "is_system": False,
        }

    async def delete_agent(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, agent_id: str,
    ) -> None:
        """Delete a custom agent. Invalidates org agents cache."""
        result = await db.execute(
            select(CmsAgent).where(CmsAgent.id == agent_id, CmsAgent.org_id == org_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise CmsException(error_code=ErrorCode.AGENT_NOT_FOUND, detail="Agent not found", status_code=404)

        await db.delete(agent)
        await db.commit()

        inv = CacheInvalidation(cache)
        await inv.clear_org_agents(org_id)

        logger.info(f"Custom agent deleted: {agent.codename} in org {org_id}")

    async def enable_system_agent(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, agent_id: str,
    ) -> dict:
        """Enable a system agent for this org. Invalidates org agents cache."""
        agent = await db.get(CmsAgent, agent_id)
        if not agent or agent.org_id is not None:
            raise CmsException(error_code=ErrorCode.AGENT_NOT_FOUND, detail="System agent not found", status_code=404)

        result = await db.execute(
            select(CmsOrgAgent).where(CmsOrgAgent.agent_id == agent_id, CmsOrgAgent.org_id == org_id)
        )
        org_agent = result.scalar_one_or_none()
        if org_agent:
            org_agent.is_enabled = True
        else:
            org_agent = CmsOrgAgent(org_id=org_id, agent_id=agent_id, is_enabled=True)
            db.add(org_agent)

        await db.commit()

        inv = CacheInvalidation(cache)
        await inv.clear_org_agents(org_id)

        return {"status": "enabled", "agent_id": agent_id}

    async def disable_system_agent(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, agent_id: str,
    ) -> dict:
        """Disable a system agent for this org. Invalidates org agents cache."""
        result = await db.execute(
            select(CmsOrgAgent).where(CmsOrgAgent.agent_id == agent_id, CmsOrgAgent.org_id == org_id)
        )
        org_agent = result.scalar_one_or_none()
        if org_agent:
            org_agent.is_enabled = False
            await db.commit()

        inv = CacheInvalidation(cache)
        await inv.clear_org_agents(org_id)

        return {"status": "disabled", "agent_id": agent_id}


# Singleton
tenant_agent_svc = TenantAgentService()
