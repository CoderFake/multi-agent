"""
Tenant agent service — custom agent CRUD + system agent enable/disable.
Uses CacheService.get_or_set() for reads + CacheInvalidation on mutation.
"""
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.config.settings import settings
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation
from app.models.agent import CmsAgent, CmsOrgAgent
from app.models.provider import CmsAgentProvider, CmsProvider, CmsAgentModel
from app.utils.logging import get_logger
from app.utils import datetime_utils

logger = get_logger(__name__)


class TenantAgentService:
    """Agent management within an org — custom CRUD + system enable/disable."""

    async def list_agents(self, db: AsyncSession, cache: CacheService, org_id: str) -> list[dict]:
        """List available agents: system enabled + org custom agents. Cached.
        Includes provider/model mapping info per agent."""

        async def _fetch():
            # Aliases for joins
            prov_alias = aliased(CmsProvider)
            model_alias = aliased(CmsAgentModel)

            # --- System agents ---
            result = await db.execute(
                select(CmsAgent, CmsOrgAgent, CmsAgentProvider, prov_alias, model_alias)
                .outerjoin(CmsOrgAgent, and_(CmsOrgAgent.agent_id == CmsAgent.id, CmsOrgAgent.org_id == org_id))
                .outerjoin(CmsAgentProvider, and_(
                    CmsAgentProvider.agent_id == CmsAgent.id,
                    CmsAgentProvider.org_id == org_id,
                    CmsAgentProvider.is_active.is_(True),
                ))
                .outerjoin(prov_alias, prov_alias.id == CmsAgentProvider.provider_id)
                .outerjoin(model_alias, model_alias.id == CmsAgentProvider.model_id)
                .where(CmsAgent.org_id.is_(None), CmsAgent.is_active.is_(True))
            )
            system_agents = []
            for agent, org_agent, mapping, provider, model in result.all():
                system_agents.append({
                    "id": str(agent.id),
                    "codename": agent.codename,
                    "display_name": agent.display_name,
                    "description": agent.description,
                    "is_active": agent.is_active,
                    "is_system": True,
                    "is_enabled": org_agent.is_enabled if org_agent else (True if agent.is_public else False),
                    "is_public": org_agent.is_public if org_agent else (True if agent.is_public else False),
                    "config_override": org_agent.config_override if org_agent else None,
                    # Provider / model mapping
                    "provider_id": str(mapping.provider_id) if mapping else None,
                    "model_id": str(mapping.model_id) if mapping else None,
                    "provider_name": provider.name if provider else None,
                    "model_name": model.name if model else None,
                    "has_provider": mapping is not None,
                })

            # --- Custom (org) agents ---
            result = await db.execute(
                select(CmsAgent, CmsOrgAgent, CmsAgentProvider, prov_alias, model_alias)
                .outerjoin(CmsOrgAgent, and_(CmsOrgAgent.agent_id == CmsAgent.id, CmsOrgAgent.org_id == org_id))
                .outerjoin(CmsAgentProvider, and_(
                    CmsAgentProvider.agent_id == CmsAgent.id,
                    CmsAgentProvider.org_id == org_id,
                    CmsAgentProvider.is_active.is_(True),
                ))
                .outerjoin(prov_alias, prov_alias.id == CmsAgentProvider.provider_id)
                .outerjoin(model_alias, model_alias.id == CmsAgentProvider.model_id)
                .where(CmsAgent.org_id == org_id)
            )
            custom_agents = []
            for agent, org_agent, mapping, provider, model in result.all():
                custom_agents.append({
                    "id": str(agent.id),
                    "codename": agent.codename,
                    "display_name": agent.display_name,
                    "description": agent.description,
                    "is_active": agent.is_active,
                    "is_system": False,
                    "is_enabled": agent.is_active,
                    "is_public": org_agent.is_public if org_agent else False,
                    "config_override": agent.default_config,
                    # Provider / model mapping
                    "provider_id": str(mapping.provider_id) if mapping else None,
                    "model_id": str(mapping.model_id) if mapping else None,
                    "provider_name": provider.name if provider else None,
                    "model_name": model.name if model else None,
                    "has_provider": mapping is not None,
                })

            return system_agents + custom_agents

        return await cache.get_or_set(
            CacheKeys.org_agents(org_id), _fetch, ttl=settings.CACHE_AGENT_TTL,
        ) or []

    async def create_agent(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, codename: str, display_name: str,
        description: str = None, default_config: dict = None,
        provider_id: str = None, model_id: str = None,
    ) -> dict:
        """Create a custom agent. Optionally link to provider/model. Invalidates org agents cache."""
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
        await db.flush()

        # Create agent ↔ provider mapping if both provided
        provider_name = None
        model_name = None
        if provider_id and model_id:
            mapping = CmsAgentProvider(
                org_id=org_id,
                agent_id=agent.id,
                provider_id=provider_id,
                model_id=model_id,
                is_active=True,
            )
            db.add(mapping)

            # Fetch names for response
            provider = await db.get(CmsProvider, provider_id)
            model = await db.get(CmsAgentModel, model_id)
            provider_name = provider.name if provider else None
            model_name = model.name if model else None

        await db.commit()
        await db.refresh(agent)

        inv = CacheInvalidation(cache)
        await inv.clear_org_agents(org_id)

        logger.info(f"Custom agent created: {agent.codename} in org {org_id}")
        return {
            "id": str(agent.id), "codename": agent.codename,
            "display_name": agent.display_name, "description": agent.description,
            "is_active": agent.is_active, "is_system": False,
            "provider_id": provider_id, "model_id": model_id,
            "provider_name": provider_name, "model_name": model_name,
            "has_provider": bool(provider_id and model_id),
        }

    async def update_agent(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, agent_id: str, **kwargs,
    ) -> dict:
        """Update a custom agent. Handles provider/model mapping upsert. Invalidates org agents cache."""
        result = await db.execute(
            select(CmsAgent).where(CmsAgent.id == agent_id, CmsAgent.org_id == org_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            raise CmsException(error_code=ErrorCode.AGENT_NOT_FOUND, detail="Agent not found", status_code=404)

        # Extract provider/model from kwargs (not agent fields)
        provider_id = kwargs.pop("provider_id", None)
        model_id = kwargs.pop("model_id", None)

        # Update agent fields
        for key, value in kwargs.items():
            if value is not None and hasattr(agent, key):
                setattr(agent, key, value)

        # Upsert agent-provider mapping
        provider_name = None
        model_name = None
        has_provider = False
        if provider_id and model_id:
            # Find existing mapping
            result = await db.execute(
                select(CmsAgentProvider).where(
                    CmsAgentProvider.agent_id == agent_id,
                    CmsAgentProvider.org_id == org_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.provider_id = provider_id
                existing.model_id = model_id
                existing.is_active = True
            else:
                db.add(CmsAgentProvider(
                    org_id=org_id, agent_id=agent_id,
                    provider_id=provider_id, model_id=model_id,
                    is_active=True,
                ))

            provider = await db.get(CmsProvider, provider_id)
            model = await db.get(CmsAgentModel, model_id)
            provider_name = provider.name if provider else None
            model_name = model.name if model else None
            has_provider = True
        else:
            # Check if existing mapping
            result = await db.execute(
                select(CmsAgentProvider, CmsProvider, CmsAgentModel)
                .outerjoin(CmsProvider, CmsProvider.id == CmsAgentProvider.provider_id)
                .outerjoin(CmsAgentModel, CmsAgentModel.id == CmsAgentProvider.model_id)
                .where(
                    CmsAgentProvider.agent_id == agent_id,
                    CmsAgentProvider.org_id == org_id,
                )
            )
            row = result.first()
            if row:
                mapping, provider, model = row
                provider_id = str(mapping.provider_id)
                model_id = str(mapping.model_id)
                provider_name = provider.name if provider else None
                model_name = model.name if model else None
                has_provider = True

        await db.commit()
        await db.refresh(agent)

        inv = CacheInvalidation(cache)
        await inv.clear_org_agents(org_id)

        return {
            "id": str(agent.id), "codename": agent.codename,
            "display_name": agent.display_name, "description": agent.description,
            "is_active": agent.is_active, "is_system": False,
            "provider_id": provider_id, "model_id": model_id,
            "provider_name": provider_name, "model_name": model_name,
            "has_provider": has_provider,
        }

    async def set_agent_provider(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, agent_id: str, provider_id: str, model_id: str,
    ) -> dict:
        """Set/update provider+model for any agent (system or custom) in this org.
        Used for system agents that are enabled in the org."""
        # Verify agent exists
        agent = await db.get(CmsAgent, agent_id)
        if not agent:
            raise CmsException(error_code=ErrorCode.AGENT_NOT_FOUND, detail="Agent not found", status_code=404)

        # Upsert mapping
        result = await db.execute(
            select(CmsAgentProvider).where(
                CmsAgentProvider.agent_id == agent_id,
                CmsAgentProvider.org_id == org_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.provider_id = provider_id
            existing.model_id = model_id
            existing.is_active = True
        else:
            db.add(CmsAgentProvider(
                org_id=org_id, agent_id=agent_id,
                provider_id=provider_id, model_id=model_id,
                is_active=True,
            ))

        await db.commit()

        # Fetch names for response
        provider = await db.get(CmsProvider, provider_id)
        model = await db.get(CmsAgentModel, model_id)

        inv = CacheInvalidation(cache)
        await inv.clear_org_agents(org_id)

        return {
            "agent_id": agent_id,
            "provider_id": provider_id,
            "model_id": model_id,
            "provider_name": provider.name if provider else None,
            "model_name": model.name if model else None,
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
