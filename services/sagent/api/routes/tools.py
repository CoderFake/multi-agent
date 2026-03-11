"""Generic tool schema & options endpoints.

Serves JSON Schema and dropdown options for any agent's form-based tools.
Each agent registers its tools in two dicts:
  - SCHEMA_REGISTRY: tool → Pydantic model
  - OPTIONS_REGISTRY: tool → {provider, build_options, client_factory}

Adding a new agent's forms:
  1. Create Pydantic models + _build_options function in the agent.
  2. Register both in the agent's `schema/_registry.py`.
  3. Import and merge below. Frontend needs ZERO changes.
"""

import logging

from fastapi import APIRouter, Header, Body
from fastapi.responses import JSONResponse

from agents.mcp_agents.redmine.schema._registry import (
    SCHEMA_REGISTRY as REDMINE_SCHEMAS,
    OPTIONS_REGISTRY as REDMINE_OPTIONS,
)
from services.oauth import get_oauth_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])

# ── Global registries — merge all agents here ─────────────────────────────────

GLOBAL_SCHEMA_REGISTRY: dict[str, dict[str, type]] = {
    "redmine": REDMINE_SCHEMAS,
    # Future: "gitlab": GITLAB_SCHEMAS, etc.
}

GLOBAL_OPTIONS_REGISTRY: dict[str, dict[str, dict]] = {
    "redmine": REDMINE_OPTIONS,
    # Future: "gitlab": GITLAB_OPTIONS, etc.
}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/{tool_name}/schema")
def get_tool_schema(tool_name: str, agent: str | None = None) -> JSONResponse:
    """Return the JSON Schema for a tool's input model."""
    model_class = None
    if agent:
        model_class = GLOBAL_SCHEMA_REGISTRY.get(agent, {}).get(tool_name)
    else:
        # Fallback: search across all agents
        for registry in GLOBAL_SCHEMA_REGISTRY.values():
            if tool_name in registry:
                model_class = registry[tool_name]
                break

    if not model_class:
        return JSONResponse(
            status_code=404,
            content={"error": f"No schema registered for tool: '{tool_name}'"},
        )
    return JSONResponse(content=model_class.model_json_schema())


@router.post("/{tool_name}/options")
async def get_tool_options(
    tool_name: str,
    agent: str | None = None,
    context: dict = Body(default_factory=dict),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> JSONResponse:
    """Return dropdown enum data for a tool's form fields.

    Fully generic: looks up the tool in OPTIONS_REGISTRY, gets credentials
    for the registered provider, creates the matching client, and calls
    the registered build_options function.

    Works for ANY agent — no agent-specific code in this file.
    """
    if not x_user_id:
        return JSONResponse(status_code=401, content={"error": "Missing X-User-Id header"})

    entry = None
    if agent:
        entry = GLOBAL_OPTIONS_REGISTRY.get(agent, {}).get(tool_name)
    else:
        # Fallback: search across all agents
        for registry in GLOBAL_OPTIONS_REGISTRY.values():
            if tool_name in registry:
                entry = registry[tool_name]
                break

    if not entry:
        # Tool exists but has no dropdowns — return empty
        return JSONResponse(content={})

    provider = entry["provider"]
    build_fn = entry["build_options"]
    client_factory = entry["client_factory"]

    try:
        conn = get_oauth_connection(user_id=x_user_id, provider=provider)
        if not conn:
            return JSONResponse(
                status_code=404,
                content={"error": f"No {provider} connection found. Please connect in Settings."},
            )

        # Create client using agent-specific factory
        base_url = conn.scopes or ""
        api_key = conn.access_token
        client = client_factory(base_url=base_url, api_key=api_key)

        # Call agent-specific options builder
        options = await build_fn(tool_name, context, client)
        return JSONResponse(content=options)

    except Exception as e:
        logger.error("Failed to fetch options for tool '%s' (provider=%s): %s", tool_name, provider, e)
        return JSONResponse(status_code=500, content={"error": f"Failed to fetch options: {str(e)}"})
