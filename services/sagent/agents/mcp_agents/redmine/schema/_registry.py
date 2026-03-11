"""Schema + options registry for Redmine agent tools.

SCHEMA_REGISTRY: maps tool_name → Pydantic model (for JSON Schema).
OPTIONS_REGISTRY: maps tool_name → options provider config (for dropdown data).

Both are merged into global registries in `api/routes/tools.py`.
To add an agent: just create these two dicts and register in the global merge.
"""

from agents.mcp_agents.redmine.client import RedmineClient
from agents.mcp_agents.redmine.schema.create_issue import CreateIssueInput
from agents.mcp_agents.redmine.schema.log_time import LogTimeInput
from agents.mcp_agents.redmine.schema.issues import UpdateIssueInput
from agents.mcp_agents.redmine.schema.projects import CreateProjectInput
from agents.mcp_agents.redmine.schema.versions import CreateVersionInput
from agents.mcp_agents.redmine.schema.wiki import UpdateWikiPageInput
from agents.mcp_agents.redmine.tools import _build_options

_REDMINE_CLIENT = lambda base_url, api_key: RedmineClient(base_url=base_url, api_key=api_key)
_REDMINE_ENTRY = lambda: {"provider": "redmine", "build_options": _build_options, "client_factory": _REDMINE_CLIENT}

# ── Schema registry (tool → Pydantic model) ─────────────────────────────────
SCHEMA_REGISTRY: dict[str, type] = {
    "create_issue":             CreateIssueInput,
    "log_time":                 LogTimeInput,
    "update_issue":             UpdateIssueInput,
    "create_project":           CreateProjectInput,
    "create_version":           CreateVersionInput,
    "update_wiki_page":         UpdateWikiPageInput,
}

# ── Options registry (tool → provider config for dropdown fetching) ──────────
# Every form-capable tool is registered here. _build_options handles routing.
OPTIONS_REGISTRY: dict[str, dict] = {
    "create_issue":             _REDMINE_ENTRY(),
    "log_time":                 _REDMINE_ENTRY(),
    "update_issue":             _REDMINE_ENTRY(),
    "create_project":           _REDMINE_ENTRY(),
    "create_version":           _REDMINE_ENTRY(),
    "update_wiki_page":         _REDMINE_ENTRY(),
}
