from pydantic import BaseModel
from typing import Dict, List, Any, Optional


class MCPConfig(BaseModel):
    """MCP Configuration Model"""
    id: str
    name: str
    protocol: str
    config: Dict[str, Any]
    tools: List[Dict[str, Any]] = []


class MCPImportRequest(BaseModel):
    """Request model for importing MCP"""
    name: Optional[str] = None
    protocol: str  # "sse" or "stdio"
    config: Dict[str, Any]


class MCPResponse(BaseModel):
    """Response model for MCP operations"""
    id: str
    name: str
    protocol: str
    tools_count: int


class ChatMessage(BaseModel):
    """Chat message model"""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request model for chat"""
    message: str
    thread_id: Optional[str] = "default"


class ApprovalRequest(BaseModel):
    """Request model for human approval"""
    thread_id: str
    approved: bool


class ToolCallInfo(BaseModel):
    """Information about a pending tool call"""
    tool_name: str
    arguments: Dict[str, Any]
    description: Optional[str] = None
