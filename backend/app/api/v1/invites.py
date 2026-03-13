"""
Invite API — create, confirm, revoke, resend invitations.
Thin router — all logic in invite_svc.
Uses permission-based access control (invite.create, invite.view, etc.).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.dependencies import get_db_session, get_redis, require_permission, get_current_user
from app.common.types import CurrentUser
from app.schemas.invite import InviteCreate, InviteConfirm, InviteResponse
from app.schemas.common import SuccessResponse
from app.cache.service import CacheService
from app.services.invite import invite_svc
from app.services.audit import audit_svc

router = APIRouter(prefix="/invites", tags=["invites"])


@router.post("", response_model=InviteResponse, status_code=201)
async def create_invite(
    data: InviteCreate,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    user: CurrentUser = Depends(require_permission("invite.create")),
):
    """Create an invitation (owner, admin, or users with invite.create permission)."""
    invite = await invite_svc.create_invite(
        db, redis, email=data.email, org_id=data.org_id,
        org_role=data.org_role.value, invited_by=user.user_id,
    )
    await audit_svc.log_action(
        db, user.user_id, "create", "invite", str(invite.id),
        new_values={"email": data.email, "org_id": data.org_id},
    )
    return invite


@router.post("/confirm")
async def confirm_invite(
    data: InviteConfirm,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
):
    """Confirm invitation — create user + membership (public endpoint)."""
    result = await invite_svc.confirm_invite(
        db, redis, token=data.token,
    )
    return result


@router.get("", response_model=list[InviteResponse])
async def list_invites(
    org_id: str,
    status: str | None = None,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("invite.view")),
):
    """List invites for an org."""
    invites = await invite_svc.list_invites(db, org_id, status)
    return invites


@router.delete("/{invite_id}", response_model=SuccessResponse)
async def revoke_invite(
    invite_id: str,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    user: CurrentUser = Depends(require_permission("invite.revoke")),
):
    """Revoke a pending invitation."""
    await invite_svc.revoke_invite(db, redis, invite_id)
    await audit_svc.log_action(db, user.user_id, "delete", "invite", invite_id)
    return {"message": "Invitation revoked"}


@router.post("/{invite_id}/resend", response_model=InviteResponse)
async def resend_invite(
    invite_id: str,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    user: CurrentUser = Depends(require_permission("invite.resend")),
):
    """Resend invitation with new token."""
    invite = await invite_svc.resend_invite(db, redis, invite_id)
    return invite
