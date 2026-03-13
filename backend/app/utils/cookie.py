
from app.common.constants import CookieConstants
from app.config.settings import settings

def _set_auth_cookies(response, access_token: str, refresh_token: str) -> None:
    """Set JWT tokens as HttpOnly cookies."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=CookieConstants.COOKIE_SECURE,
        samesite=CookieConstants.COOKIE_SAMESITE_ACCESS_TOKEN,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=CookieConstants.COOKIE_SECURE,
        samesite=CookieConstants.COOKIE_SAMESITE_REFRESH_TOKEN,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth/refresh",
    )


def _clear_auth_cookies(response) -> None:
    """Clear JWT cookies."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")

