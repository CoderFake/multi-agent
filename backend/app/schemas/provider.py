"""
Provider schemas — request/response models for provider endpoints.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import CmsBaseSchema, StrUUID


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
