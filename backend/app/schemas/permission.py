"""
Permission schemas — response models for permission endpoints.
"""
from typing import Optional

from pydantic import BaseModel


class PermissionResponse(BaseModel):
    """Permission response."""
    id: str
    codename: str
    name: str
    content_type: str  # "app_label.model"

    class Config:
        from_attributes = True


class PermCheckRequest(BaseModel):
    """POST /permissions/check — test permission."""
    user_id: str
    codename: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None


class PermCheckResponse(BaseModel):
    """Permission check result."""
    granted: bool
    reason: str  # "superuser", "user_override", "group", "denied"


class UserPermissionsResponse(BaseModel):
    """All resolved permissions for a user in an org."""
    user_id: str
    org_id: str
    permissions: list[str]  # list of codenames
    groups: list[str]  # list of group names


class UIPermissionsResponse(BaseModel):
    """UI-specific permissions for frontend rendering."""
    user_id: str
    org_id: str
    nav_items: list[str]  # visible nav item codenames
    actions: dict[str, list[str]]  # resource_type → allowed actions
