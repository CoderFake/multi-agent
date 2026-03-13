"""
Cache key generators for Redis.
Centralized key management following naming conventions.
"""


class CacheKeys:
    """Cache key generators with consistent naming patterns."""

    # ── User & Auth ──────────────────────────────────────────────────────

    @staticmethod
    def user_info(user_id: str) -> str:
        """Cache key for user info."""
        return f"user:{user_id}"

    @staticmethod
    def user_permissions(user_id: str, org_id: str) -> str:
        """Cache key for resolved user permissions in an org."""
        return f"perm:{org_id}:{user_id}"

    @staticmethod
    def blacklist(jti: str) -> str:
        """Cache key for blacklisted JWT token (TTL = token lifetime)."""
        return f"blacklist:{jti}"

    @staticmethod
    def membership(user_id: str, org_id: str) -> str:
        """Cache key for user's org membership (role + active status)."""
        return f"membership:{user_id}:{org_id}"

    @staticmethod
    def invite_password(invite_token: str) -> str:
        """Cache key for temp password of an invite (TTL = invite expiry)."""
        return f"invite_pwd:{invite_token[:16]}"

    @staticmethod
    def invite_fullname(invite_token: str) -> str:
        """Cache key for invitee full name (TTL = invite expiry)."""
        return f"invite_name:{invite_token[:16]}"

    # ── Organization ─────────────────────────────────────────────────────

    @staticmethod
    def org_config(org_id: str) -> str:
        """Cache key for organization config."""
        return f"org_config:{org_id}"

    @staticmethod
    def org_info(org_id: str) -> str:
        """Cache key for single org info."""
        return f"org:{org_id}"

    @staticmethod
    def org_users(org_id: str) -> str:
        """Cache key for org's user/member list."""
        return f"org_users:{org_id}"

    @staticmethod
    def org_groups(org_id: str) -> str:
        """Cache key for org's group list."""
        return f"org_groups:{org_id}"

    @staticmethod
    def org_agents(org_id: str) -> str:
        """Cache key for org's enabled agents list."""
        return f"org_agents:{org_id}"

    # ── System Resources (rarely change → long TTL) ──────────────────────

    @staticmethod
    def system_agents() -> str:
        """Cache key for system agents list (org_id=NULL)."""
        return "sys:agents"

    @staticmethod
    def system_providers() -> str:
        """Cache key for system providers list (org_id=NULL)."""
        return "sys:providers"

    @staticmethod
    def system_mcp_servers() -> str:
        """Cache key for system MCP servers list (org_id=NULL)."""
        return "sys:mcp_servers"

    @staticmethod
    def system_settings() -> str:
        """Cache key for system settings list."""
        return "sys:settings"

    @staticmethod
    def system_setting(key: str) -> str:
        """Cache key for a single system setting."""
        return f"sys:setting:{key}"

    # ── Provider ─────────────────────────────────────────────────────────

    @staticmethod
    def provider_keys(org_id: str, provider_id: str) -> str:
        """Cache key for provider API keys (encrypted, for rotation)."""
        return f"prov_keys:{org_id}:{provider_id}"

    # ── Agent ────────────────────────────────────────────────────────────

    @staticmethod
    def agent_config(agent_id: str, org_id: str) -> str:
        """Cache key for agent config in an org."""
        return f"agent:{agent_id}:org:{org_id}"

    @staticmethod
    def agent_mcp_servers(agent_id: str, org_id: str) -> str:
        """Cache key for MCP servers assigned to an agent in an org."""
        return f"agent_mcp:{agent_id}:{org_id}"

    @staticmethod
    def agent_mcp_toolset(agent_id: str, org_id: str) -> str:
        """Cache key for agent's full MCP toolset (servers + tools + env_overrides)."""
        return f"agent_mcp_ts:{agent_id}:{org_id}"

    # ── Group Access Control ─────────────────────────────────────────────

    @staticmethod
    def group_agents(group_id: str, org_id: str) -> str:
        """Cache key for agents accessible by a group."""
        return f"group_agents:{group_id}:{org_id}"

    @staticmethod
    def group_tools(group_id: str, org_id: str) -> str:
        """Cache key for tool access settings for a group."""
        return f"group_tools:{group_id}:{org_id}"

    @staticmethod
    def user_accessible_agents(user_id: str, org_id: str) -> str:
        """Cache key for resolved list of agents a user can access."""
        return f"user_agents:{user_id}:{org_id}"

    @staticmethod
    def user_accessible_tools(user_id: str, org_id: str) -> str:
        """Cache key for resolved list of tools a user can access."""
        return f"user_tools:{user_id}:{org_id}"
    # ── Rate Limiting ────────────────────────────────────────────────────

    @staticmethod
    def rate_limit_ip(ip_address: str) -> str:
        """Cache key for IP rate limit."""
        return f"ratelimit:ip:{ip_address}"

    @staticmethod
    def rate_limit_user(user_id: str) -> str:
        """Cache key for user rate limit."""
        return f"ratelimit:user:{user_id}"

    # ── Patterns (for bulk invalidation) ─────────────────────────────────

    @staticmethod
    def user_pattern(user_id: str = "") -> str:
        """Pattern for user cache keys."""
        if user_id:
            return f"user:{user_id}*"
        return "user:*"

    @staticmethod
    def org_pattern(org_id: str) -> str:
        """Pattern for org-related cache keys."""
        return f"*:{org_id}:*"

    @staticmethod
    def perm_pattern(org_id: str = "", user_id: str = "") -> str:
        """Pattern for permission cache keys."""
        if org_id and user_id:
            return f"perm:{org_id}:{user_id}"
        if org_id:
            return f"perm:{org_id}:*"
        return "perm:*"

    @staticmethod
    def membership_pattern(user_id: str = "", org_id: str = "") -> str:
        """Pattern for membership cache keys."""
        if user_id and org_id:
            return f"membership:{user_id}:{org_id}"
        if user_id:
            return f"membership:{user_id}:*"
        if org_id:
            return f"membership:*:{org_id}"
        return "membership:*"

    @staticmethod
    def system_pattern() -> str:
        """Pattern for all system cache keys."""
        return "sys:*"

    @staticmethod
    def group_access_pattern(org_id: str, group_id: str = "") -> str:
        """Pattern for group access cache keys."""
        if group_id:
            return f"group_*:{group_id}:{org_id}"
        return f"group_*:*:{org_id}"

    @staticmethod
    def agent_mcp_pattern(org_id: str, agent_id: str = "") -> str:
        """Pattern for agent-MCP cache keys."""
        if agent_id:
            return f"agent_mcp:{agent_id}:{org_id}"
        return f"agent_mcp:*:{org_id}"

    @staticmethod
    def agent_mcp_toolset_pattern(org_id: str, agent_id: str = "") -> str:
        """Pattern for agent-MCP toolset cache keys."""
        if agent_id:
            return f"agent_mcp_ts:{agent_id}:{org_id}"
        return f"agent_mcp_ts:*:{org_id}"

    @staticmethod
    def user_access_pattern(org_id: str, user_id: str = "") -> str:
        """Pattern for user access cache keys."""
        if user_id:
            return f"user_*:{user_id}:{org_id}"
        return f"user_*:*:{org_id}"
