"""
Auth API endpoints — login, refresh, logout, me.
No self-registration — users are invited by admins.
JWT tokens stored in HttpOnly cookies.
Token blacklisting via Redis TTL.
"""
from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.dependencies import get_db_session, get_redis, get_current_user
from app.common.types import CurrentUser
from app.services.auth import auth_svc
from app.schemas.auth import LoginRequest, MeResponse
from app.config.settings import settings
from app.core.exceptions import CmsException
from app.common.constants import ErrorCode

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie settings
COOKIE_SECURE = settings.ENVIRONMENT != "development"
COOKIE_SAMESITE = "lax"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set JWT tokens as HttpOnly cookies."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth/refresh",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear JWT cookies."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
):
    """Login with email/password → set JWT cookies."""
    user, access_token, refresh_token = await auth_svc.login(db, body.email, body.password)
    _set_auth_cookies(response, access_token, refresh_token)
    return {"message": "Login successful", "user_id": str(user.id)}


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
