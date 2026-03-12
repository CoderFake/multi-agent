"""
Auth schemas — request/response models for authentication endpoints.
No registration schema — users are invited by admins.
"""
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """POST /auth/login"""
    email: EmailStr
    password: str


class MeResponse(BaseModel):
    """GET /auth/me — current user info."""
    id: str
    email: str
    full_name: str
    is_superuser: bool
    is_active: bool
    memberships: list["OrgMembershipResponse"]

    class Config:
        from_attributes = True


class OrgMembershipResponse(BaseModel):
    """Org membership info within MeResponse."""
    org_id: str
    org_name: str
    org_slug: str
    org_role: str
    is_active: bool

    class Config:
        from_attributes = True


class TokenPayload(BaseModel):
    """Internal: JWT token payload."""
    sub: str  # user_id
    jti: str  # unique token id
    type: str  # access / refresh
