"""
Invite service — create, confirm, revoke, resend invitations.
Temp passwords stored in Redis with TTL. Follows embed_chatbot pattern.
"""
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.config.settings import settings
from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.common.enums import OrgRole
from app.cache.keys import CacheKeys
from app.models.user import CmsUser, CmsInvite
from app.models.organization import CmsOrganization, CmsOrgMembership
from app.config.settings import settings
from app.utils.hasher import hash_password
from app.utils.datetime_utils import now
from app.utils.logging import get_logger

logger = get_logger(__name__)


class InviteService:
    """Invite-based registration service."""

    async def create_invite(
        self,
        db: AsyncSession,
        redis: Redis,
        email: str,
        org_id: str,
        org_role: str,
        invited_by: str,
    ) -> CmsInvite:
        """Create an invitation. Generates token + temp password in Redis."""
        # Check org exists
        org = await db.get(CmsOrganization, org_id)
        if not org:
            raise CmsException(
                error_code=ErrorCode.ORG_NOT_FOUND,
                detail="Organization not found",
                status_code=404,
            )

        # Check if user already exists and is already a member
        existing_user = await db.execute(
            select(CmsUser).where(CmsUser.email == email, CmsUser.deleted_at.is_(None))
        )
        existing = existing_user.scalar_one_or_none()
        if existing:
            membership = await db.execute(
                select(CmsOrgMembership).where(
                    CmsOrgMembership.user_id == existing.id,
                    CmsOrgMembership.org_id == org_id,
                )
            )
            if membership.scalar_one_or_none():
                raise CmsException(
                    error_code=ErrorCode.ORG_MEMBERSHIP_EXISTS,
                    detail="User is already a member of this organization",
                    status_code=409,
                )

        # Check for pending invite
        pending = await db.execute(
            select(CmsInvite).where(
                CmsInvite.email == email,
                CmsInvite.org_id == org_id,
                CmsInvite.status == "pending",
            )
        )
        if pending.scalar_one_or_none():
            raise CmsException(
                error_code="INVITE_ALREADY_PENDING",
                detail="A pending invitation already exists for this email",
                status_code=409,
            )

        # Generate token and temp password
        token = secrets.token_urlsafe(32)
        temp_password = secrets.token_urlsafe(settings.INVITE_TEMP_PASSWORD_LENGTH)
        expires_at = now() + timedelta(hours=settings.INVITE_EXPIRE_HOURS)

        # Store temp password in Redis with TTL
        redis_ttl = settings.INVITE_EXPIRE_HOURS * 3600
        await redis.setex(
            CacheKeys.invite_password(token),
            redis_ttl,
            temp_password,
        )

        # Create invite record
        invite = CmsInvite(
            email=email,
            token=token,
            org_id=org_id,
            org_role=org_role,
            invited_by=invited_by,
            status="pending",
            expires_at=expires_at,
        )
        db.add(invite)
        await db.commit()
        await db.refresh(invite)

        logger.info(f"Invite created for {email} to org {org_id} by {invited_by}")
        return invite

    async def confirm_invite(
        self,
        db: AsyncSession,
        redis: Redis,
        token: str,
        full_name: str,
        password: str,
    ) -> CmsUser:
        """Confirm invitation: create user + membership, invalidate invite."""
        # Find invite
        result = await db.execute(
            select(CmsInvite).where(
                CmsInvite.token == token,
                CmsInvite.status == "pending",
            )
        )
        invite = result.scalar_one_or_none()
        if not invite:
            raise CmsException(
                error_code="INVITE_NOT_FOUND",
                detail="Invalid or expired invitation",
                status_code=404,
            )

        # Check expiry
        if invite.expires_at < now():
            invite.status = "expired"
            await db.commit()
            raise CmsException(
                error_code="INVITE_EXPIRED",
                detail="This invitation has expired",
                status_code=410,
            )

        # Check if user already exists
        existing = await db.execute(
            select(CmsUser).where(CmsUser.email == invite.email, CmsUser.deleted_at.is_(None))
        )
        user = existing.scalar_one_or_none()

        if not user:
            # Create new user
            user = CmsUser(
                email=invite.email,
                full_name=full_name,
                hashed_password=hash_password(password),
                is_active=True,
                is_superuser=False,
            )
            db.add(user)
            await db.flush()

        # Create membership
        membership = CmsOrgMembership(
            user_id=user.id,
            org_id=invite.org_id,
            org_role=invite.org_role,
            is_active=True,
        )
        db.add(membership)

        # Mark invite as accepted
        invite.status = "accepted"
        await db.commit()
        await db.refresh(user)

        # Clean up Redis temp password
        await redis.delete(CacheKeys.invite_password(token))

        logger.info(f"Invite confirmed: {invite.email} joined org {invite.org_id}")
        return user

    async def revoke_invite(self, db: AsyncSession, redis: Redis, invite_id: str) -> None:
        """Revoke a pending invitation."""
        invite = await db.get(CmsInvite, invite_id)
        if not invite or invite.status != "pending":
            raise CmsException(
                error_code="INVITE_NOT_FOUND",
                detail="Pending invitation not found",
                status_code=404,
            )

        invite.status = "revoked"
        await db.commit()

        # Clean up Redis
        await redis.delete(CacheKeys.invite_password(invite.token))
        logger.info(f"Invite {invite_id} revoked")

    async def resend_invite(self, db: AsyncSession, redis: Redis, invite_id: str) -> CmsInvite:
        """Resend invitation — regenerate token + extend expiry."""
        invite = await db.get(CmsInvite, invite_id)
        if not invite or invite.status != "pending":
            raise CmsException(
                error_code="INVITE_NOT_FOUND",
                detail="Pending invitation not found",
                status_code=404,
            )

        # Clean old Redis key
        await redis.delete(CacheKeys.invite_password(invite.token))

        # Regenerate
        new_token = secrets.token_urlsafe(32)
        temp_password = secrets.token_urlsafe(settings.INVITE_TEMP_PASSWORD_LENGTH)
        invite.token = new_token
        invite.expires_at = now() + timedelta(hours=settings.INVITE_EXPIRE_HOURS)

        # Store new temp password
        await redis.setex(
            CacheKeys.invite_password(new_token),
            settings.INVITE_EXPIRE_HOURS * 3600,
            temp_password,
        )

        await db.commit()
        await db.refresh(invite)
        logger.info(f"Invite {invite_id} resent with new token")
        return invite

    async def list_invites(self, db: AsyncSession, org_id: str, status: str | None = None) -> list[CmsInvite]:
        """List invites for an org."""
        query = select(CmsInvite).where(CmsInvite.org_id == org_id)
        if status:
            query = query.where(CmsInvite.status == status)
        query = query.order_by(CmsInvite.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())


# Singleton
invite_svc = InviteService()
