"""
Security utilities: JWT token management.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt, JWTError

from app.config.settings import settings
from app.common.enums import TokenType
from app.core.exceptions import CmsException
from app.common.constants import ErrorCode


def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token with JTI for blacklisting."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": user_id,
        "jti": str(uuid.uuid4()),
        "type": TokenType.ACCESS.value,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """Create JWT refresh token with longer TTL and JTI."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    payload = {
        "sub": user_id,
        "jti": str(uuid.uuid4()),
        "type": TokenType.REFRESH.value,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises CmsException on failure."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise CmsException(
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
            detail="Invalid or expired token",
            status_code=401,
        )
