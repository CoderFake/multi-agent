"""
Auth schemas — request/response models for authentication endpoints.
No registration schema — users are invited by admins.
"""
from pydantic import BaseModel, EmailStr

from app.schemas.common import CmsBaseSchema, StrUUID


class LoginRequest(BaseModel):
    """POST /auth/login"""
    email: EmailStr
    password: str


class MeResponse(CmsBaseSchema):
    """GET /auth/me — current user info."""
    id: StrUUID
    email: str
    full_name: str
    is_superuser: bool
    is_active: bool
    avatar_url: str | None = None
    memberships: list["OrgMembershipResponse"]


class OrgMembershipResponse(CmsBaseSchema):
    """Org membership info within MeResponse."""
    org_id: StrUUID
    org_name: str
    org_slug: str
    org_logo_url: str | None = None
    org_role: str
    is_active: bool
    timezone: str = "UTC"


class TokenPayload(BaseModel):
    """Internal: JWT token payload."""
    sub: str  # user_id
    jti: str  # unique token id
    type: str  # access / refresh


class ChangePasswordRequest(BaseModel):
    """POST /auth/change-password"""
    current_password: str
    new_password: str
