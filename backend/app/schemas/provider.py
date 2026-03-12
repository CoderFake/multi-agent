"""
Provider schemas — request/response models for provider endpoints.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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


class ProviderResponse(BaseModel):
    """Provider response."""
    id: str
    name: str
    slug: str
    api_base_url: Optional[str] = None
    auth_type: str
    is_active: bool
    org_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
