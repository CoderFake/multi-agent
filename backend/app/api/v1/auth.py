"""
Auth API endpoints — login, refresh, logout, me.
No self-registration — users are invited by admins.
JWT tokens stored in HttpOnly cookies.
Token blacklisting via Redis TTL.
"""
from fastapi import APIRouter, Depends, Response, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.dependencies import get_db_session, get_redis, get_current_user, get_cache_service
from app.common.types import CurrentUser
from app.services.auth import auth_svc
from app.cache.invalidation import CacheService
from app.schemas.auth import LoginRequest, MeResponse, ChangePasswordRequest
from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.utils.cookie import _set_auth_cookies, _clear_auth_cookies
from app.utils.request_utils import get_request_origin

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
):
    """Login with email/password → set JWT cookies."""
    user, access_token, refresh_token, must_change = await auth_svc.login(db, body.email, body.password)
    _set_auth_cookies(response, access_token, refresh_token)
    return {
        "message": "Login successful",
        "user_id": str(user.id),
        "must_change_password": must_change,
    }


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
):
    """Refresh access token using refresh token cookie. Rotates both tokens."""
    refresh_token_str = request.cookies.get("refresh_token")
    if not refresh_token_str:
        raise CmsException(
            error_code=ErrorCode.AUTH_REFRESH_TOKEN_INVALID,
            detail="Refresh token not found",
            status_code=401,
        )

    new_access, new_refresh = await auth_svc.refresh(db, redis, refresh_token_str)
    _set_auth_cookies(response, new_access, new_refresh)
    return {"message": "Token refreshed"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    redis: Redis = Depends(get_redis),
):
    """Logout — blacklist tokens in Redis + clear cookies."""
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")

    if access_token:
        await auth_svc.logout(redis, access_token, refresh_token)

    _clear_auth_cookies(response)
    return {"message": "Logout successful"}


@router.get("/me", response_model=MeResponse)
async def me(
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get current user info + org memberships."""
    return await auth_svc.get_me(db, current_user.user_id)


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user),
    cache: CacheService = Depends(get_cache_service),
):
    """Upload user avatar to S3. Returns public URL."""
    avatar_url = await auth_svc.update_avatar(db, current_user.user_id, file, cache=cache)
    return {"avatar_url": avatar_url}


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Change user password. Required after first login with temp password."""
    await auth_svc.change_password(
        db, current_user.user_id, body.current_password, body.new_password,
    )
    return {"message": "Password changed successfully"}
