"""
Schemas for agent access control — agent-MCP, group-agent, group-tool.
"""
from pydantic import BaseModel


# ── Agent ↔ MCP Server ──────────────────────────────────────────────────

class AgentMcpAttach(BaseModel):
    """Attach an MCP server to an agent."""
    mcp_server_id: str


class AgentMcpResponse(BaseModel):
    id: str
    agent_id: str
    mcp_server_id: str
    mcp_server_codename: str | None = None
    mcp_server_name: str | None = None
    is_active: bool


# ── Group ↔ Agent ────────────────────────────────────────────────────────

class GroupAgentAssign(BaseModel):
    """Assign agents to a group."""
    agent_ids: list[str]


class GroupAgentResponse(BaseModel):
    id: str
    group_id: str
    agent_id: str
    agent_codename: str | None = None
    agent_name: str | None = None


# ── Group ↔ Tool Access ─────────────────────────────────────────────────

class GroupToolToggle(BaseModel):
    """Toggle tool access for a group."""
    tool_id: str
    is_enabled: bool


class GroupToolBulkToggle(BaseModel):
    """Bulk toggle tools for a group."""
    entries: list[GroupToolToggle]


class GroupToolAccessResponse(BaseModel):
    id: str
    group_id: str
    tool_id: str
    tool_codename: str | None = None
    tool_name: str | None = None
    is_enabled: bool


# ── Org Agent update ────────────────────────────────────────────────────

class OrgAgentPublicToggle(BaseModel):
    """Toggle is_public flag for an org agent."""
    is_public: bool
