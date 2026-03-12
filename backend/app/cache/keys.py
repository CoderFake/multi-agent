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
    def invite_password(invite_token: str) -> str:
        """Cache key for temp password of an invite (TTL = invite expiry)."""
        return f"invite_pwd:{invite_token[:16]}"

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
    def system_pattern() -> str:
        """Pattern for all system cache keys."""
        return "sys:*"
