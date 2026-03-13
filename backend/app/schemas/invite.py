"""
Invite schemas — request/response models for invite endpoints.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.common.enums import OrgRole
from app.schemas.common import CmsBaseSchema, StrUUID


class InviteCreate(BaseModel):
    """POST /invites — create invite."""
    email: EmailStr
    org_id: str
    org_role: OrgRole = OrgRole.MEMBER


class InviteConfirm(BaseModel):
    """POST /invites/confirm — accept invite."""
    token: str


class InviteResponse(CmsBaseSchema):
    """Invite response."""
    id: StrUUID
    email: str
    org_id: StrUUID
    org_role: str
    status: str
    invited_by_email: Optional[str] = None
    expires_at: datetime
    created_at: datetime


class InviteResend(BaseModel):
    """POST /invites/{id}/resend."""
    invite_id: str
