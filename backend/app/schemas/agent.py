"""
Agent schemas — request/response models for agent endpoints.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.schemas.common import CmsBaseSchema, StrUUID


class AgentCreate(BaseModel):
    """POST /system/agents."""
    codename: str
    display_name: str
    description: Optional[str] = None
    default_config: Optional[dict[str, Any]] = None
    provider_id: Optional[str] = None
    model_id: Optional[str] = None


class AgentUpdate(BaseModel):
    """PUT /system/agents/{id}."""
    display_name: Optional[str] = None
    description: Optional[str] = None
    default_config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None
    provider_id: Optional[str] = None
    model_id: Optional[str] = None


class AgentResponse(CmsBaseSchema):
    """Agent response."""
    id: StrUUID
    codename: str
    display_name: str
    description: Optional[str] = None
    default_config: Optional[dict[str, Any]] = None
    is_active: bool
    is_public: bool = False
    org_id: Optional[StrUUID] = None  # None = system agent
    created_at: datetime


class AgentOrgAssignment(BaseModel):
    """PUT /system/agents/{id}/orgs — bulk assign orgs."""
    org_ids: list[str]


class AgentOrgResponse(CmsBaseSchema):
    """Org assignment for an agent."""
    org_id: StrUUID
    org_name: str
    is_enabled: bool


class AgentToolResponse(CmsBaseSchema):
    """Tool assigned to a system agent."""
    id: StrUUID
    codename: str
    display_name: str
    description: Optional[str] = None
    server_name: str


class SetPublicBody(BaseModel):
    is_public: bool


class SetAgentProviderBody(BaseModel):
    provider_id: str
    model_id: str
