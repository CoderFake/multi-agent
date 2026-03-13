"""
Invite service — create, confirm, revoke, resend invitations.
Temp passwords stored in Redis with TTL = invite expiry.
Email sent via RabbitMQ worker (non-blocking).
Notification to superuser inviter on accept.
"""
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.config.settings import settings
from app.core.exceptions import CmsException
from app.common.constants import ErrorCode, InviteStatus, NotificationType, NotificationCode
from app.cache.keys import CacheKeys
from app.models.user import CmsUser, CmsInvite
from app.models.organization import CmsOrganization, CmsOrgMembership
from app.utils.hasher import hash_password
from app.utils.datetime_utils import now
from app.utils.logging import get_logger
from app.utils.request_utils import build_org_frontend_url
from app.services.notification import notification_svc
from app.utils.email_queue import queue_email
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation

logger = get_logger(__name__)


class InviteService:
    """Invite-based registration service."""

    def _generate_random_password(self, length: int = 16) -> str:
        """Generate secure random password."""
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Ensure at least one of each type
        if not any(c.islower() for c in password):
            password = password[:-1] + secrets.choice(string.ascii_lowercase)
        if not any(c.isupper() for c in password):
            password = password[:-2] + secrets.choice(string.ascii_uppercase) + password[-1]
        if not any(c.isdigit() for c in password):
            password = password[:-3] + secrets.choice(string.digits) + password[-2:]
        return password

    async def create_invite(
        self,
        db: AsyncSession,
        redis: Redis,
        email: str,
        org_id: str,
        org_role: str,
        invited_by: str,
        full_name: str | None = None,
    ) -> CmsInvite:
        """
        Create invitation, store temp password in Redis, queue email.
        TTL in Redis = invite expire time (they are the same).
        """
        # Check org exists
        org = await db.get(CmsOrganization, org_id)
        if not org:
            raise CmsException(
                error_code=ErrorCode.ORG_NOT_FOUND,
                detail="Organization not found",
                status_code=404,
            )

        # Check if user already exists and is already a member
        existing_user_result = await db.execute(
            select(CmsUser).where(CmsUser.email == email, CmsUser.deleted_at.is_(None))
        )
        existing = existing_user_result.scalar_one_or_none()
        if existing:
            membership_result = await db.execute(
                select(CmsOrgMembership).where(
                    CmsOrgMembership.user_id == existing.id,
                    CmsOrgMembership.org_id == org_id,
                )
            )
            if membership_result.scalar_one_or_none():
                raise CmsException(
                    error_code=ErrorCode.ORG_MEMBERSHIP_EXISTS,
                    detail="User is already a member of this organization",
                    status_code=409,
                )

        # Check for pending invite
        pending_result = await db.execute(
            select(CmsInvite).where(
                CmsInvite.email == email,
                CmsInvite.org_id == org_id,
                CmsInvite.status == InviteStatus.PENDING,
            )
        )
        if pending_result.scalar_one_or_none():
            raise CmsException(
                error_code="INVITE_ALREADY_PENDING",
                detail="A pending invitation already exists for this email",
                status_code=409,
            )

        # Generate token and temp password
        token = secrets.token_urlsafe(32)
        temp_password = self._generate_random_password(settings.INVITE_TEMP_PASSWORD_LENGTH)

        # TTL = invite expiry (same value)
        redis_ttl = settings.INVITE_EXPIRE_HOURS * 3600
        expires_at = now() + __import__("datetime").timedelta(seconds=redis_ttl)

        # Store temp password in Redis
        await redis.setex(
            CacheKeys.invite_password(token),
            redis_ttl,
            temp_password,
        )
        # Store full_name if provided
        if full_name:
            await redis.setex(
                CacheKeys.invite_fullname(token),
                redis_ttl,
                full_name,
            )

        # Check for existing revoked/expired invite to reuse
        existing_invite_result = await db.execute(
            select(CmsInvite).where(
                CmsInvite.email == email,
                CmsInvite.org_id == org_id,
                CmsInvite.status.in_([InviteStatus.REVOKED, InviteStatus.EXPIRED]),
            ).order_by(CmsInvite.created_at.desc())
        )
        existing_invite = existing_invite_result.scalar_one_or_none()

        if existing_invite:
            # Reuse existing invite record
            if existing_invite.token:
                await redis.delete(CacheKeys.invite_password(existing_invite.token))
                await redis.delete(CacheKeys.invite_fullname(existing_invite.token))
            existing_invite.token = token
            existing_invite.org_role = org_role
            existing_invite.invited_by = invited_by
            existing_invite.status = InviteStatus.PENDING
            existing_invite.expires_at = expires_at
            existing_invite.accepted_at = None
            await db.flush()
            await db.refresh(existing_invite)
            invite = existing_invite
        else:
            # Create new invite record
            invite = CmsInvite(
                email=email,
                token=token,
                org_id=org_id,
                org_role=org_role,
                invited_by=invited_by,
                status=InviteStatus.PENDING,
                expires_at=expires_at,
            )
            db.add(invite)
            await db.flush()
            await db.refresh(invite)

        logger.info(f"Invite created for {email} to org {org.name} ({org.subdomain})")

        # ── Queue invite email (non-blocking via RabbitMQ worker) ────────
        inviter_result = await db.execute(
            select(CmsUser).where(CmsUser.id == invited_by, CmsUser.deleted_at.is_(None))
        )
        inviter = inviter_result.scalar_one_or_none()
        inviter_name = inviter.full_name if inviter else "Admin"

        base_url = build_org_frontend_url(org.subdomain)
        accept_url = f"{base_url}/accept-invite#token={token}"

        try:
            await queue_email(
                template_name="invite.html",
                recipient_email=email,
                subject=f"Invitation to join {org.name}",
                context={
                    "app_name": settings.APP_NAME,
                    "organization_name": org.name,
                    "subdomain": org.subdomain or org.slug,
                    "inviter_name": inviter_name,
                    "role": org_role.replace("_", " ").title(),
                    "email": email,
                    "password": temp_password,
                    "accept_url": accept_url,
                    "expire_hours": settings.INVITE_EXPIRE_HOURS,
                },
                priority=7,
            )
        except Exception as e:
            logger.error(f"Failed to queue invite email: {e}", exc_info=True)
            # Don't fail the invite creation if email queue fails

        await db.commit()
        return invite

    async def confirm_invite(
        self,
        db: AsyncSession,
        redis: Redis,
        token: str
    ) -> dict:
        """
        Accept invite: create user with random password, create membership.
        Notify inviter (superuser) that owner accepted.
        Returns dict with email for frontend display.
        """
        # Find invite
        result = await db.execute(
            select(CmsInvite).where(
                CmsInvite.token == token,
                CmsInvite.status == InviteStatus.PENDING,
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
            invite.status = InviteStatus.EXPIRED
            await db.commit()
            raise CmsException(
                error_code="INVITE_EXPIRED",
                detail="This invitation has expired",
                status_code=410,
            )

        # Get temp password from Redis
        password_key = CacheKeys.invite_password(token)
        stored_password = await redis.get(password_key)
        if not stored_password:
            raise CmsException(
                error_code="INVITE_EXPIRED",
                detail="Invite credentials expired",
                status_code=410,
            )
        temp_password = stored_password.decode() if isinstance(stored_password, bytes) else stored_password

        # Get full_name from Redis
        fullname_key = CacheKeys.invite_fullname(token)
        cached_name = await redis.get(fullname_key)
        if cached_name:
            full_name = cached_name.decode() if isinstance(cached_name, bytes) else cached_name
        else:
            full_name = invite.email.split("@")[0]

        # Check if user exists
        existing_result = await db.execute(
            select(CmsUser).where(CmsUser.email == invite.email, CmsUser.deleted_at.is_(None))
        )
        user = existing_result.scalar_one_or_none()

        if user:
            if user.last_login is None:
                user.hashed_password = hash_password(temp_password)
        else:
            user = CmsUser(
                email=invite.email,
                full_name=full_name,
                hashed_password=hash_password(temp_password),
                is_active=True,
                is_superuser=False,
                last_login=None,
            )
            db.add(user)
            await db.flush()

        # Create membership
        existing_membership = await db.execute(
            select(CmsOrgMembership).where(
                CmsOrgMembership.user_id == user.id,
                CmsOrgMembership.org_id == invite.org_id,
            )
        )
        if not existing_membership.scalar_one_or_none():
            membership = CmsOrgMembership(
                user_id=user.id,
                org_id=invite.org_id,
                org_role=invite.org_role,
                is_active=True,
                joined_at=now(),
            )
            db.add(membership)

        # Mark invite as accepted
        invite.status = InviteStatus.ACCEPTED
        invite.accepted_at = now()

        # Clean up Redis
        await redis.delete(password_key)
        fullname_key = CacheKeys.invite_fullname(token)
        await redis.delete(fullname_key)

        await db.commit()

        # ── Invalidate caches so new member appears immediately ─────────


        cache_svc = CacheService(redis)
        inv = CacheInvalidation(cache_svc)
        await inv.clear_org_users(str(invite.org_id))
        await inv.clear_org_memberships(str(invite.org_id))
        await inv.clear_membership(str(user.id), str(invite.org_id))

        # ── Notify inviter (superuser) ──────────────────────────────────
        try:
            await notification_svc.create(
                db, str(invite.invited_by), str(invite.org_id),
                NotificationType.INVITE_ACCEPTED,
                NotificationCode.INVITE_ACCEPTED,
                NotificationCode.INVITE_ACCEPTED_DESC,
                {"email": invite.email, "org_role": invite.org_role},
            )
        except Exception as e:
            logger.warning(f"Failed to notify inviter: {e}")

        logger.info(f"Invite confirmed: {invite.email} joined org {invite.org_id}")
        return {"email": invite.email, "message": "Invitation accepted successfully"}

    async def revoke_invite(self, db: AsyncSession, redis: Redis, invite_id: str) -> None:
        """Revoke a pending invitation."""
        invite = await db.get(CmsInvite, invite_id)
        if not invite or invite.status != InviteStatus.PENDING:
            raise CmsException(
                error_code="INVITE_NOT_FOUND",
                detail="Pending invitation not found",
                status_code=404,
            )

        invite.status = InviteStatus.REVOKED
        await db.commit()

        # Clean up Redis
        await redis.delete(CacheKeys.invite_password(invite.token))
        await redis.delete(CacheKeys.invite_fullname(invite.token))
        logger.info(f"Invite {invite_id} revoked")

    async def resend_invite(self, db: AsyncSession, redis: Redis, invite_id: str) -> CmsInvite:
        """Resend invitation — regenerate token + password, queue email again."""
        invite = await db.get(CmsInvite, invite_id)
        if not invite or invite.status != InviteStatus.PENDING:
            raise CmsException(
                error_code="INVITE_NOT_FOUND",
                detail="Pending invitation not found",
                status_code=404,
            )

        # Clean old Redis keys
        await redis.delete(CacheKeys.invite_password(invite.token))
        await redis.delete(CacheKeys.invite_fullname(invite.token))

        # Regenerate token + password
        new_token = secrets.token_urlsafe(32)
        new_password = self._generate_random_password(settings.INVITE_TEMP_PASSWORD_LENGTH)

        redis_ttl = settings.INVITE_EXPIRE_HOURS * 3600
        invite.token = new_token
        invite.expires_at = now() + __import__("datetime").timedelta(seconds=redis_ttl)

        # Store new password in Redis
        await redis.setex(
            CacheKeys.invite_password(new_token),
            redis_ttl,
            new_password,
        )

        await db.commit()
        await db.refresh(invite)

        # Get org + inviter info for email
        org = await db.get(CmsOrganization, str(invite.org_id))
        inviter_result = await db.execute(
            select(CmsUser).where(CmsUser.id == invite.invited_by, CmsUser.deleted_at.is_(None))
        )
        inviter = inviter_result.scalar_one_or_none()
        inviter_name = inviter.full_name if inviter else "Admin"

        base_url = build_org_frontend_url(org.subdomain if org else None)
        accept_url = f"{base_url}/accept-invite#token={new_token}"

        try:
            await queue_email(
                template_name="invite.html",
                recipient_email=invite.email,
                subject=f"Invitation to join {org.name}" if org else "Invitation resent",
                context={
                    "app_name": settings.APP_NAME,
                    "organization_name": org.name if org else "Unknown",
                    "subdomain": (org.subdomain or org.slug) if org else "",
                    "inviter_name": inviter_name,
                    "role": invite.org_role.replace("_", " ").title(),
                    "email": invite.email,
                    "password": new_password,
                    "accept_url": accept_url,
                    "expire_hours": settings.INVITE_EXPIRE_HOURS,
                },
                priority=7,
            )
        except Exception as e:
            logger.error(f"Failed to queue resend invite email: {e}", exc_info=True)

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
