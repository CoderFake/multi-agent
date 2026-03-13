"""
MCP schemas — request/response models for MCP server and tool endpoints.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.schemas.common import CmsBaseSchema, StrUUID


class McpServerCreate(BaseModel):
    """POST /system/mcp-servers."""
    codename: str
    display_name: str
    transport: str = "stdio"
    connection_config: Optional[dict[str, Any]] = None
    requires_env_vars: bool = False
    is_public: bool = False


class McpServerUpdate(BaseModel):
    """PUT /system/mcp-servers/{id}."""
    display_name: Optional[str] = None
    transport: Optional[str] = None
    connection_config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    requires_env_vars: Optional[bool] = None
    is_public: Optional[bool] = None


class McpServerResponse(CmsBaseSchema):
    """MCP server response."""
    id: StrUUID
    codename: str
    display_name: str
    transport: str
    connection_config: Optional[dict[str, Any]] = None
    requires_env_vars: bool = False
    is_active: bool
    is_public: bool = False
    org_id: Optional[StrUUID] = None
    created_at: datetime


class ToolCreate(BaseModel):
    """POST /system/mcp-servers/{id}/tools."""
    codename: str
    display_name: str
    description: Optional[str] = None
    input_schema: Optional[dict[str, Any]] = None


class ToolUpdate(BaseModel):
    """PUT /tools/{id}."""
    display_name: Optional[str] = None
    description: Optional[str] = None
    input_schema: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class ToolResponse(CmsBaseSchema):
    """Tool response."""
    id: StrUUID
    mcp_server_id: StrUUID
    codename: str
    display_name: str
    description: Optional[str] = None
    input_schema: Optional[dict[str, Any]] = None
    is_active: bool
    created_at: datetime


# ── Tool Discovery ────────────────────────────────────────────────────

class McpDiscoverRequest(BaseModel):
    """POST /system/mcp-servers/discover-tools — parse MCP JSON and discover tools."""
    mcp_config: dict[str, Any]
    """
    Standard MCP config format:
    {
        "mcpServers": {
            "server-name": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-gitlab"],
                "env": {"GITLAB_API_URL": "..."}
            }
        }
    }
    """


class DiscoveredTool(BaseModel):
    """A tool discovered from an MCP server."""
    name: str
    description: Optional[str] = None
    input_schema: Optional[dict[str, Any]] = None


class McpDiscoverResponse(BaseModel):
    """Response from tool discovery."""
    server_name: str
    tools: list[DiscoveredTool]
    error: Optional[str] = None


# ── Org Assignment ────────────────────────────────────────────────────

class McpOrgAssign(BaseModel):
    """PUT /system/mcp-servers/{id}/orgs — set assigned orgs."""
    org_ids: list[str]
