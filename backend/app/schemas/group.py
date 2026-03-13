"""
Tenant group schemas — CRUD + permission assignment.
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.common import CmsBaseSchema, StrUUID


class GroupCreate(BaseModel):
    """Create a group within an org."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class GroupUpdate(BaseModel):
    """Update a group."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class GroupResponse(CmsBaseSchema):
    """Group info."""
    id: StrUUID
    org_id: Optional[StrUUID] = None
    name: str
    description: Optional[str] = None
    is_system_default: bool = False
    member_count: int = 0
    permission_count: int = 0


class GroupListResponse(BaseModel):
    """Paginated group list."""
    items: list[GroupResponse]
    total: int


class PermissionAssign(BaseModel):
    """Assign/revoke permissions to a group."""
    permission_ids: list[str] = Field(..., min_length=1)


class GroupMemberAction(BaseModel):
    """Add/remove a user from a group."""
    user_id: str
