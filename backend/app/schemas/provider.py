"""
Provider schemas — request/response models for provider + key + agent-mapping endpoints.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import CmsBaseSchema, StrUUID


# ── System Provider ──────────────────────────────────────────────────────

class ProviderCreate(BaseModel):
    """POST /system/providers."""
    name: str
    slug: str
    api_base_url: Optional[str] = None
    auth_type: str = "api_key"


class ProviderUpdate(BaseModel):
    """PUT /system/providers/{id}."""
    name: Optional[str] = None
    api_base_url: Optional[str] = None
    auth_type: Optional[str] = None
    is_active: Optional[bool] = None


class ProviderResponse(CmsBaseSchema):
    """Provider response."""
    id: StrUUID
    name: str
    slug: str
    api_base_url: Optional[str] = None
    auth_type: str
    is_active: bool
    org_id: Optional[StrUUID] = None
    created_at: datetime


# ── Provider Key (Tenant) ────────────────────────────────────────────────

class ProviderKeyCreate(BaseModel):
    """POST /tenant/providers/{provider_id}/keys."""
    api_key: str
    priority: int = 1


class ProviderKeyUpdate(BaseModel):
    """PUT /tenant/providers/keys/{key_id}."""
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class ProviderKeyResponse(CmsBaseSchema):
    """Provider key response (key masked)."""
    id: StrUUID
    provider_id: StrUUID
    org_id: StrUUID
    key_preview: str  # last 4 chars only
    priority: int
    is_active: bool
    last_used_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    created_at: datetime


# ── Agent ↔ Provider ↔ Model Mapping (Tenant) ────────────────────────────

class AgentProviderCreate(BaseModel):
    """POST /tenant/providers/agent-mapping."""
    agent_id: str
    provider_id: str
    model_id: str
    config_override: Optional[dict] = None


class AgentProviderUpdate(BaseModel):
    """PUT /tenant/providers/agent-mapping/{id}."""
    model_id: Optional[str] = None
    config_override: Optional[dict] = None
    is_active: Optional[bool] = None


class AgentProviderResponse(CmsBaseSchema):
    """Agent ↔ Provider ↔ Model mapping response."""
    id: StrUUID
    org_id: StrUUID
    agent_id: StrUUID
    provider_id: StrUUID
    model_id: StrUUID
    config_override: Optional[dict] = None
    is_active: bool


# ── Agent Model ──────────────────────────────────────────────────────────

class ModelCreate(BaseModel):
    """POST /system/providers/{id}/models."""
    name: str
    model_type: str = "chat"
    context_window: Optional[int] = None
    pricing_per_1m_tokens: Optional[float] = None


class ModelUpdate(BaseModel):
    """PUT /system/providers/{id}/models/{model_id}."""
    name: Optional[str] = None
    model_type: Optional[str] = None
    context_window: Optional[int] = None
    pricing_per_1m_tokens: Optional[float] = None
    is_active: Optional[bool] = None


class AgentModelResponse(CmsBaseSchema):
    """Model definition response."""
    id: StrUUID
    provider_id: StrUUID
    name: str
    model_type: str
    context_window: Optional[int] = None
    pricing_per_1m_tokens: Optional[float] = None
    is_active: bool
    created_at: datetime
