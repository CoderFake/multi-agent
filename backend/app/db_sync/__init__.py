"""
DB Sync — database synchronization & seed operations.
Modular structure for managing permissions, providers, agents, tools, etc.

Usage from code:
    from app.db_sync import sync_permissions, sync_default_groups, sync_superuser
    from app.db_sync import sync_providers, sync_models
    from app.db_sync import sync_agents
    from app.db_sync import sync_tool_servers, sync_tools

CLI usage:
    uv run python -m app.init_db
"""

from app.db_sync.permissions import (
    sync_permissions,
    sync_default_groups,
    CONTENT_TYPES,
    PERMISSIONS,
    DEFAULT_GROUPS,
)
from app.db_sync.providers import (
    sync_providers,
    sync_models,
    PROVIDERS,
    MODELS,
)
from app.db_sync.agents import (
    sync_agents,
    SYSTEM_AGENTS,
)
from app.db_sync.tools import (
    sync_tool_servers,
    sync_tools,
    TOOL_SERVERS,
    TOOLS,
    AGENT_TOOLS,
)
from app.db_sync.superuser import sync_superuser

__all__ = [
    # Permissions & groups
    "sync_permissions",
    "sync_default_groups",
    "CONTENT_TYPES",
    "PERMISSIONS",
    "DEFAULT_GROUPS",
    # Providers & models
    "sync_providers",
    "sync_models",
    "PROVIDERS",
    "MODELS",
    # Agents
    "sync_agents",
    "SYSTEM_AGENTS",
    # Tools
    "sync_tool_servers",
    "sync_tools",
    "TOOL_SERVERS",
    "TOOLS",
    "AGENT_TOOLS",
    # Users
    "sync_superuser",
]
