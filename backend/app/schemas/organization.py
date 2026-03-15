"""
Organization schemas — request/response models for organization management.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.schemas.common import CmsBaseSchema, StrUUID


class OrgCreate(BaseModel):
    """POST /system/organizations."""
    name: str
    subdomain: str
    timezone: str = "UTC"

    @field_validator("subdomain")
    @classmethod
    def validate_subdomain(cls, v: str) -> str:
        v = v.lower().strip()
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Subdomain must be alphanumeric with hyphens/underscores")
        return v


class OrgUpdate(BaseModel):
    """PUT /system/organizations/{id}."""
    name: Optional[str] = None
    subdomain: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


class TenantOrgUpdate(BaseModel):
    """PATCH /tenant/settings — tenant-level org update (organization.update permission)."""
    name: Optional[str] = None
    timezone: Optional[str] = None


class OrgResponse(CmsBaseSchema):
    """Organization response."""
    id: StrUUID
    name: str
    slug: str
    subdomain: Optional[str] = None
    logo_url: Optional[str] = None
    timezone: str
    is_active: bool
    created_at: datetime


class OrgListResponse(OrgResponse):
    """Organization list response with member count."""
    member_count: int = 0


class MembershipResponse(CmsBaseSchema):
    """Org membership response."""
    user_id: StrUUID
    user_email: str
    user_full_name: str
    org_role: str
    is_active: bool
    joined_at: datetime


class AddMemberRequest(BaseModel):
    """POST /system/organizations/{id}/members — always owner."""
    user_id: str
