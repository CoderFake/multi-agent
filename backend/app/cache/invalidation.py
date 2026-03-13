"""
Cache invalidation helpers.
Called from services on data mutations to clear stale cache entries.
Stub methods — implementation grows as services are added.
"""
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CacheInvalidation:
    """Centralized cache invalidation methods."""

    def __init__(self, cache: CacheService):
        self.cache = cache

    async def clear_user_permissions(self, user_id: str, org_id: str) -> None:
        """Invalidate cached permissions for a user in an org."""
        key = CacheKeys.user_permissions(user_id, org_id)
        await self.cache.delete(key)
        logger.info(f"Invalidated user permissions cache: {key}")

    async def clear_org_users(self, org_id: str) -> None:
        """Invalidate cached user list for an org."""
        key = CacheKeys.org_users(org_id)
        await self.cache.delete(key)
        logger.info(f"Invalidated org users cache: {key}")

    async def clear_org_groups(self, org_id: str) -> None:
        """Invalidate cached group list for an org."""
        key = CacheKeys.org_groups(org_id)
        await self.cache.delete(key)
        logger.info(f"Invalidated org groups cache: {key}")

    async def clear_org_agents(self, org_id: str) -> None:
        """Invalidate cached agent list for an org."""
        key = CacheKeys.org_agents(org_id)
        await self.cache.delete(key)
        logger.info(f"Invalidated org agents cache: {key}")

    async def clear_provider_keys(self, org_id: str, provider_id: str) -> None:
        """Invalidate cached provider keys for an org."""
        key = CacheKeys.provider_keys(org_id, provider_id)
        await self.cache.delete(key)
        logger.info(f"Invalidated provider keys cache: {key}")

    async def clear_user_info(self, user_id: str) -> None:
        """Invalidate cached user info."""
        key = CacheKeys.user_info(user_id)
        await self.cache.delete(key)
        logger.info(f"Invalidated user info cache: {key}")

    async def clear_org_config(self, org_id: str) -> None:
        """Invalidate cached org config."""
        key = CacheKeys.org_config(org_id)
        await self.cache.delete(key)
        logger.info(f"Invalidated org config cache: {key}")

    async def clear_org_info(self, org_id: str) -> None:
        """Invalidate cached org info."""
        key = CacheKeys.org_info(org_id)
        await self.cache.delete(key)
        logger.info(f"Invalidated org info cache: {key}")

    # ── System Resources ─────────────────────────────────────────────────

    async def clear_system_agents(self) -> None:
        """Invalidate system agents list cache."""
        await self.cache.delete(CacheKeys.system_agents())
        logger.info("Invalidated system agents cache")

    async def clear_system_providers(self) -> None:
        """Invalidate system providers list cache."""
        await self.cache.delete(CacheKeys.system_providers())
        logger.info("Invalidated system providers cache")

    async def clear_system_mcp_servers(self) -> None:
        """Invalidate system MCP servers list cache."""
        await self.cache.delete(CacheKeys.system_mcp_servers())
        logger.info("Invalidated system MCP servers cache")

    async def clear_system_settings(self) -> None:
        """Invalidate all system settings cache."""
        await self.cache.delete(CacheKeys.system_settings())
        # Also clear pattern for individual settings
        await self.cache.delete_pattern("sys:setting:*")
        logger.info("Invalidated system settings cache")

    async def clear_system_setting(self, key: str) -> None:
        """Invalidate a single system setting + the list cache."""
        await self.cache.delete(CacheKeys.system_setting(key))
        await self.cache.delete(CacheKeys.system_settings())
        logger.info(f"Invalidated system setting cache: {key}")

    # ── Bulk ──────────────────────────────────────────────────────────────

    async def clear_all_org_permissions(self, org_id: str) -> None:
        """Invalidate all user permissions in an org (e.g. group change)."""
        pattern = CacheKeys.perm_pattern(org_id=org_id)
        await self.cache.delete_pattern(pattern)
        logger.info(f"Invalidated all permissions for org: {org_id}")

    # ── Agent Access Control ─────────────────────────────────────────────

    async def clear_agent_mcp_servers(self, agent_id: str, org_id: str) -> None:
        """Invalidate agent's MCP server list + all user resolved access."""
        await self.cache.delete(CacheKeys.agent_mcp_servers(agent_id, org_id))
        await self.cache.delete_pattern(CacheKeys.user_access_pattern(org_id))
        logger.info(f"Invalidated agent MCP servers cache: agent={agent_id}, org={org_id}")

    async def clear_group_agents(self, group_id: str, org_id: str) -> None:
        """Invalidate group-agent access + all user resolved agent access."""
        await self.cache.delete(CacheKeys.group_agents(group_id, org_id))
        await self.cache.delete_pattern(CacheKeys.user_access_pattern(org_id))
        logger.info(f"Invalidated group agents cache: group={group_id}, org={org_id}")

    async def clear_group_tools(self, group_id: str, org_id: str) -> None:
        """Invalidate group-tool access + all user resolved tool access."""
        await self.cache.delete(CacheKeys.group_tools(group_id, org_id))
        await self.cache.delete_pattern(CacheKeys.user_access_pattern(org_id))
        logger.info(f"Invalidated group tools cache: group={group_id}, org={org_id}")

    async def clear_all_access_control(self, org_id: str) -> None:
        """Invalidate ALL access control caches for an org (nuclear option)."""
        await self.cache.delete_pattern(CacheKeys.group_access_pattern(org_id))
        await self.cache.delete_pattern(CacheKeys.agent_mcp_pattern(org_id))
        await self.cache.delete_pattern(CacheKeys.user_access_pattern(org_id))
        await self.clear_org_agents(org_id)
        logger.info(f"Invalidated all access control caches for org: {org_id}")
