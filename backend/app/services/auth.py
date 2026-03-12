"""
Auth service — login, refresh, logout with JWT HttpOnly cookies.
Token blacklisting via Redis TTL (no DB table needed).
No self-registration — users are invited by admins.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.config.settings import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.utils.hasher import verify_password
from app.utils.datetime_utils import now
from app.utils.logging import get_logger
from app.models.user import CmsUser
from app.models.organization import CmsOrgMembership, CmsOrganization
from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.cache.keys import CacheKeys

logger = get_logger(__name__)


class AuthService:
    """Authentication service singleton."""

    async def login(self, db: AsyncSession, email: str, password: str) -> tuple[CmsUser, str, str]:
        """Verify credentials and return (user, access_token, refresh_token)."""
        result = await db.execute(
            select(CmsUser).where(CmsUser.email == email, CmsUser.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise CmsException(
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                detail="Invalid email or password",
                status_code=401,
            )

        if not user.is_active:
            raise CmsException(
                error_code=ErrorCode.AUTH_ACCOUNT_DISABLED,
                detail="Account is disabled",
                status_code=403,
            )

        # Update last login
        user.last_login = now()
        await db.commit()

        # Generate tokens
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        return user, access_token, refresh_token

    async def refresh(self, db: AsyncSession, redis: Redis, refresh_token_str: str) -> tuple[str, str]:
        """Refresh access token. Rotates refresh token, blacklists old one in Redis."""
        payload = decode_token(refresh_token_str)

        if payload.get("type") != "refresh":
            raise CmsException(
                error_code=ErrorCode.AUTH_TOKEN_INVALID,
                detail="Invalid refresh token",
                status_code=401,
            )

        user_id = payload.get("sub")
        jti = payload.get("jti")

        # Check blacklist in Redis
        if jti and await redis.exists(CacheKeys.blacklist(jti)):
            raise CmsException(
                error_code=ErrorCode.AUTH_TOKEN_REVOKED,
                detail="Token has been revoked",
                status_code=401,
            )

        # Verify user
        result = await db.execute(
            select(CmsUser).where(
                CmsUser.id == user_id,
                CmsUser.is_active.is_(True),
                CmsUser.deleted_at.is_(None),
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise CmsException(
                error_code=ErrorCode.AUTH_USER_NOT_FOUND,
                detail="User not found",
                status_code=401,
            )

        # Blacklist old refresh token in Redis (TTL = remaining time)
        if jti:
            exp = payload.get("exp", 0)
            remaining_ttl = max(int(exp - now().timestamp()), 60)
            await redis.setex(CacheKeys.blacklist(jti), remaining_ttl, "1")

        # Issue new tokens
        new_access = create_access_token(str(user.id))
        new_refresh = create_refresh_token(str(user.id))

        return new_access, new_refresh

    async def logout(self, redis: Redis, access_token_str: str, refresh_token_str: str | None = None) -> None:
        """Blacklist tokens in Redis with TTL = token remaining lifetime."""
        try:
            payload = decode_token(access_token_str)
            jti = payload.get("jti")
            if jti:
                ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
                await redis.setex(CacheKeys.blacklist(jti), ttl, "1")
        except Exception:
            pass

        if refresh_token_str:
            try:
                payload = decode_token(refresh_token_str)
                jti = payload.get("jti")
                if jti:
                    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
                    await redis.setex(CacheKeys.blacklist(jti), ttl, "1")
            except Exception:
                pass

    async def get_me(self, db: AsyncSession, user_id: str) -> dict:
        """Get current user info with org memberships."""
        result = await db.execute(
            select(CmsUser).where(CmsUser.id == user_id, CmsUser.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise CmsException(
                error_code=ErrorCode.AUTH_USER_NOT_FOUND,
                detail="User not found",
                status_code=404,
            )

        # Get memberships
        memberships_result = await db.execute(
            select(CmsOrgMembership, CmsOrganization)
            .join(CmsOrganization, CmsOrgMembership.org_id == CmsOrganization.id)
            .where(CmsOrgMembership.user_id == user_id, CmsOrgMembership.is_active.is_(True))
        )
        memberships = []
        for membership, org in memberships_result.all():
            memberships.append({
                "org_id": str(membership.org_id),
                "org_name": org.name,
                "org_slug": org.slug,
                "org_role": membership.org_role,
                "is_active": membership.is_active,
            })

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_superuser": user.is_superuser,
            "is_active": user.is_active,
            "memberships": memberships,
        }


# Singleton
auth_svc = AuthService()
