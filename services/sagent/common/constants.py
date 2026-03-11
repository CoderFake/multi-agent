"""Application-wide constants.

Single source of truth for magic strings and values used across layers.
"""

# ADK uses agent name as app_name for session/artifact scoping
APP_NAME = "root_agent"

AGENT_ICONS = {
    "search": "search",
    "data_analyst": "database",
    "team_knowledge": "file-text",
    "gitlab": "git-merge",
}

AGENT_NAMES = {
    "gitlab": "Gitlab Assistant",
}

# Maps the `x-enabled-agents` frontend ID values to actual backend ADK Tool instance names
FRONTEND_AGENT_KEYS_TO_BACKEND_TOOLS = {
    "web_search": "web_search",
    "team_knowledge": "team_knowledge_agent",
    "data_analyst": "data_analyst_agent",
    "gitlab": "gitlab",
}

AVAILABLE_SUB_AGENT_TOOLS = {"web_search", "team_knowledge_agent", "data_analyst_agent", "gitlab"}