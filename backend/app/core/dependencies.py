"""
FastAPI dependencies for dependency injection.
Re-exports infrastructure deps from database.py + auth deps.
"""
import json

from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.core.database import get_db as get_db_session, get_redis  # re-export
from app.core.security import decode_token
from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.common.types import CurrentUser
from app.models.user import CmsUser
from app.models.organization import CmsOrgMembership
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.services.permission import permission_svc
from app.config.settings import settings


# ── Infrastructure Deps ────────────────────────────────────────────────

def get_cache_service(redis: Redis = Depends(get_redis)) -> "CacheService":
    """Returns a CacheService wrapping the Redis client."""
    return CacheService(redis)


# ── Auth Deps ──────────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> CurrentUser:
    """
    Read JWT from HttpOnly cookie, verify, check Redis blacklist, return CurrentUser.
    User info (email, is_superuser) is cached in Redis to avoid DB query on every request.
    Invalidated by: clear_user_info(user_id)
    """
    token = request.cookies.get("access_token")
    if not token:
        raise CmsException(
            error_code=ErrorCode.AUTH_NOT_AUTHENTICATED,
            detail="Not authenticated",
            status_code=401,
        )

    payload = decode_token(token)  # raises CmsException on invalid

    # Check token type
    if payload.get("type") != "access":
        raise CmsException(
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
            detail="Invalid token type",
            status_code=401,
        )

    # Check blacklist in Redis (TTL = token lifetime, auto-expires)
    jti = payload.get("jti")
    if jti and await redis.exists(CacheKeys.blacklist(jti)):
        raise CmsException(
            error_code=ErrorCode.AUTH_TOKEN_REVOKED,
            detail="Token has been revoked",
            status_code=401,
        )

    user_id = payload.get("sub")

    # ── Try Redis cache first ───────────────────────────────────────
    cache_key = CacheKeys.user_info(user_id)
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        if not data.get("is_active", True):
            raise CmsException(
                error_code=ErrorCode.AUTH_USER_NOT_FOUND,
                detail="User not found",
                status_code=401,
            )
        return CurrentUser(
            user_id=user_id,
            email=data["email"],
            is_superuser=data.get("is_superuser", False),
            org_id=None,
            org_role=None,
            groups=[],
        )

    # ── Cache miss → query DB ───────────────────────────────────────
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

    # Write to cache
    await redis.setex(cache_key, settings.AUTH_CACHE_TTL, json.dumps({
        "email": user.email,
        "is_superuser": user.is_superuser,
        "is_active": user.is_active,
    }))

    return CurrentUser(
        user_id=str(user.id),
        email=user.email,
        is_superuser=user.is_superuser,
        org_id=None,
        org_role=None,
        groups=[],
    )


async def require_superuser(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Dependency: requires the current user to be a superuser."""
    if not current_user.is_superuser:
        raise CmsException(
            error_code=ErrorCode.AUTH_FORBIDDEN,
            detail="Superuser access required",
            status_code=403,
        )
    return current_user


async def require_org_membership(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """
    Dependency: requires user to be a member of the org.
    Membership (org_role) is cached in Redis to avoid DB query on every request.
    Invalidated by: clear_user_info(user_id), clear_org_users(org_id)

    Resolution order for org_id:
      1. Path param  :  /t/{org_id}/...
      2. Header      :  X-Org-Id
      3. Query param :  ?org_id=...
      4. Middleware   :  request.state.org_id (subdomain resolver)
    """
    org_id = (
        request.path_params.get("org_id")
        or request.headers.get("x-org-id")
        or request.query_params.get("org_id")
        or getattr(request.state, "org_id", None)
    )

    if not org_id:
        raise CmsException(
            error_code=ErrorCode.ORG_NOT_FOUND,
            detail="Organization not specified",
            status_code=400,
        )

    if current_user.is_superuser:
        current_user.org_id = str(org_id)
        current_user.org_role = "superuser"
        return current_user

    # ── Try Redis cache first ───────────────────────────────────────
    cache_key = CacheKeys.membership(current_user.user_id, str(org_id))
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        if not data.get("is_active", False):
            raise CmsException(
                error_code=ErrorCode.ORG_MEMBERSHIP_REQUIRED,
                detail="You are not a member of this organization",
                status_code=403,
            )
        current_user.org_id = str(org_id)
        current_user.org_role = data["org_role"]
        return current_user

    # ── Cache miss → query DB ───────────────────────────────────────
    result = await db.execute(
        select(CmsOrgMembership).where(
            CmsOrgMembership.org_id == org_id,
            CmsOrgMembership.user_id == current_user.user_id,
            CmsOrgMembership.is_active.is_(True),
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise CmsException(
            error_code=ErrorCode.ORG_MEMBERSHIP_REQUIRED,
            detail="You are not a member of this organization",
            status_code=403,
        )

    # Write to cache
    await redis.setex(cache_key, settings.AUTH_CACHE_TTL, json.dumps({
        "org_role": membership.org_role,
        "is_active": membership.is_active,
    }))

    current_user.org_id = str(membership.org_id)
    current_user.org_role = membership.org_role
    return current_user


# ── Permission-based access control ──────────────────────────────────

def require_permission(codename: str):
    """
    Factory: returns a dependency that checks a specific permission codename.
    Uses the full RBAC chain: superuser → owner → admin → group → denied.
    Requires org_id to be resolvable (same as require_org_membership).
    """
    async def _check(
        request: Request,
        db: AsyncSession = Depends(get_db_session),
        redis: Redis = Depends(get_redis),
        user: CurrentUser = Depends(require_org_membership),
    ) -> CurrentUser:

        granted, reason = await permission_svc.check_permission(
            db, redis, user.user_id, user.org_id, codename,
        )
        if not granted:
            raise CmsException(
                error_code=ErrorCode.AUTH_FORBIDDEN,
                detail=f"Permission '{codename}' required (reason: {reason})",
                status_code=403,
            )
        return user

    return _check
