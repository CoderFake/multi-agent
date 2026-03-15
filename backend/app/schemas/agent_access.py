"""
Schemas for agent access control — agent-MCP, group-agent, group-tool.
"""
from pydantic import BaseModel

from app.schemas.common import CmsBaseSchema, StrUUID


# ── Agent ↔ MCP Server ──────────────────────────────────────────────────

class AgentMcpAssign(BaseModel):
    """Assign an MCP server to an agent."""
    mcp_server_id: str
    env_overrides: dict | None = None


class AgentMcpEnvUpdate(BaseModel):
    """Update env overrides for an agent-MCP link."""
    env_overrides: dict


class AgentMcpResponse(CmsBaseSchema):
    id: StrUUID
    agent_id: StrUUID
    mcp_server_id: StrUUID
    mcp_server_codename: str | None = None
    mcp_server_name: str | None = None
    is_active: bool
    env_overrides: dict | None = None
    requires_env_vars: bool = False
    connection_config: dict | None = None


# ── Group ↔ Agent ────────────────────────────────────────────────────────

class GroupAgentAssign(BaseModel):
    """Assign agents to a group."""
    agent_ids: list[str]


class GroupAgentResponse(CmsBaseSchema):
    id: StrUUID
    group_id: StrUUID
    agent_id: StrUUID
    agent_codename: str | None = None
    agent_name: str | None = None


# ── Group ↔ Tool Access ─────────────────────────────────────────────────

class GroupToolToggle(BaseModel):
    """Toggle tool access for a group+agent."""
    tool_id: str
    is_enabled: bool


class GroupToolBulkToggle(BaseModel):
    """Bulk toggle tools for a group."""
    entries: list[GroupToolToggle]


class GroupToolAccessResponse(CmsBaseSchema):
    id: StrUUID
    group_id: StrUUID
    agent_id: StrUUID
    tool_id: StrUUID
    tool_codename: str | None = None
    tool_name: str | None = None
    is_enabled: bool


# ── Org Agent update ────────────────────────────────────────────────────

class OrgAgentPublicToggle(BaseModel):
    """Toggle is_public flag for an org agent."""
    is_public: bool
