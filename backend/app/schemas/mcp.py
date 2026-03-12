"""
MCP schemas — request/response models for MCP server and tool endpoints.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class McpServerCreate(BaseModel):
    """POST /system/mcp-servers."""
    codename: str
    display_name: str
    transport: str = "stdio"
    connection_config: Optional[dict[str, Any]] = None


class McpServerUpdate(BaseModel):
    """PUT /system/mcp-servers/{id}."""
    display_name: Optional[str] = None
    transport: Optional[str] = None
    connection_config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class McpServerResponse(BaseModel):
    """MCP server response."""
    id: str
    codename: str
    display_name: str
    transport: str
    connection_config: Optional[dict[str, Any]] = None
    is_active: bool
    org_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


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


class ToolResponse(BaseModel):
    """Tool response."""
    id: str
    mcp_server_id: str
    codename: str
    display_name: str
    description: Optional[str] = None
    input_schema: Optional[dict[str, Any]] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
