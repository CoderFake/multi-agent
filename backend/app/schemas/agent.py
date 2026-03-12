"""
Agent schemas — request/response models for agent endpoints.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class AgentCreate(BaseModel):
    """POST /system/agents."""
    codename: str
    display_name: str
    description: Optional[str] = None
    default_config: Optional[dict[str, Any]] = None


class AgentUpdate(BaseModel):
    """PUT /system/agents/{id}."""
    display_name: Optional[str] = None
    description: Optional[str] = None
    default_config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    """Agent response."""
    id: str
    codename: str
    display_name: str
    description: Optional[str] = None
    default_config: Optional[dict[str, Any]] = None
    is_active: bool
    org_id: Optional[str] = None  # None = system agent
    created_at: datetime

    class Config:
        from_attributes = True
