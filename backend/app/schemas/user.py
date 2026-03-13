"""
Tenant user schemas — responses and updates for org-scoped user management.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.common import CmsBaseSchema, StrUUID


class UserResponse(CmsBaseSchema):
    """User info within an organization."""
    user_id: StrUUID
    email: str
    full_name: str
    org_role: str
    is_active: bool
    joined_at: Optional[datetime] = None


class UserListResponse(BaseModel):
    """Paginated user list."""
    items: list[UserResponse]
    total: int
    page: int
    page_size: int


class UserUpdate(BaseModel):
    """Update user within org — role or active status."""
    org_role: Optional[str] = Field(None, description="New org role: owner, admin, member")
    is_active: Optional[bool] = Field(None, description="Activate/deactivate membership")
