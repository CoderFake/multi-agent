"""
Invite schemas — request/response models for invite endpoints.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.common.enums import OrgRole


class InviteCreate(BaseModel):
    """POST /invites — create invite."""
    email: EmailStr
    org_id: str
    org_role: OrgRole = OrgRole.MEMBER


class InviteConfirm(BaseModel):
    """POST /invites/confirm — accept invite."""
    token: str


class InviteResponse(BaseModel):
    """Invite response."""
    id: UUID
    email: str
    org_id: UUID
    org_role: str
    status: str
    invited_by_email: Optional[str] = None
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class InviteResend(BaseModel):
    """POST /invites/{id}/resend."""
    invite_id: str
