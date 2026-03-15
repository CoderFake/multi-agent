"""
Auth service — login, refresh, logout with JWT HttpOnly cookies.
Token blacklisting via Redis TTL (no DB table needed).
No self-registration — users are invited by admins.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from fastapi import UploadFile

from app.config.settings import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.utils.hasher import verify_password, hash_password
from app.utils.datetime_utils import now
from app.utils.logging import get_logger
from app.models.user import CmsUser
from app.models.organization import CmsOrgMembership, CmsOrganization
from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation
from app.utils.storage import upload_file, delete_file, get_public_url, generate_path

logger = get_logger(__name__)


class AuthService:
    """Authentication service singleton."""

    async def login(self, db: AsyncSession, email: str, password: str) -> tuple[CmsUser, str, str, bool]:
        """Verify credentials and return (user, access_token, refresh_token, must_change_password)."""
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

        # Check if first login (last_login is None = force password change)
        must_change_password = user.last_login is None

        # Update last login
        user.last_login = now()
        await db.commit()

        # Generate tokens
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        return user, access_token, refresh_token, must_change_password

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
                "org_logo_url": get_public_url(org.logo_url, bucket=org.subdomain or org.slug),
                "org_role": membership.org_role,
                "is_active": membership.is_active,
                "timezone": org.timezone or "UTC",
            })

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_superuser": user.is_superuser,
            "is_active": user.is_active,
            "avatar_url": get_public_url(user.avatar_url, bucket=settings.BUCKET_SYSTEM),
            "memberships": memberships,
        }

    async def update_avatar(
        self, db: AsyncSession, user_id: str, file: UploadFile,
        cache: CacheService | None = None,
    ) -> str:
        """Upload avatar to S3, delete old one, update DB."""
        # Validate
        allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        if file.content_type not in allowed_types:
            raise CmsException(
                error_code="INVALID_FILE_TYPE",
                detail=f"Allowed types: {', '.join(allowed_types)}",
                status_code=400,
            )

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

        # Delete old avatar if exists
        if user.avatar_url:
            await delete_file(user.avatar_url, bucket=settings.BUCKET_SYSTEM)

        # Upload new
        path = generate_path(f"avatars/{user_id}", file.filename or "avatar.jpg")
        storage_path = await upload_file(file, path, bucket=settings.BUCKET_SYSTEM)

        # Save to DB
        user.avatar_url = storage_path
        await db.commit()

        if cache:
            inv = CacheInvalidation(cache)
            await inv.clear_user_info(user_id)

        return get_public_url(storage_path, bucket=settings.BUCKET_SYSTEM)

    async def change_password(
        self, db: AsyncSession, user_id: str,
        current_password: str, new_password: str,
    ) -> None:
        """Change user password. Used after first login with temp password."""
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

        if not verify_password(current_password, user.hashed_password):
            raise CmsException(
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                detail="Current password is incorrect",
                status_code=400,
            )

        user.hashed_password = hash_password(new_password)
        await db.commit()
        logger.info(f"Password changed for user {user_id}")


# Singleton
auth_svc = AuthService()
