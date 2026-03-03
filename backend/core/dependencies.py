"""
core/dependencies.py — FastAPI dependency for Firebase auth + DB user sync.

Flow per request:
  1. Extract Bearer token from Authorization header
  2. Verify against Firebase → get firebase_uid + claims
  3. Upsert user row in PostgreSQL (create on first login, update last_seen_at)
  4. Return User ORM object

Usage:
    from core.dependencies import get_current_user
    from models.user import User

    @router.get("/me")
    async def me(user: User = Depends(get_current_user)):
        return {"id": user.id, "email": user.email}
"""
import logging
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Verify Firebase ID token → sync to DB → return User.
    Raises HTTP 401 if token missing / invalid.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Verify Firebase token
    try:
        from core.firebase import verify_id_token
        claims = verify_id_token(credentials.credentials)
    except ValueError as e:
        logger.warning("Firebase token verification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    firebase_uid: str = claims["uid"]

    # 2. Upsert user in PostgreSQL
    user = await sync_user_from_claims(db, firebase_uid, claims)
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None instead of 401 when no token."""
    if not credentials or not credentials.credentials:
        return None
    try:
        from core.firebase import verify_id_token
        claims = verify_id_token(credentials.credentials)
        return await sync_user_from_claims(db, claims["uid"], claims)
    except (ValueError, Exception):
        return None


async def sync_user_from_claims(
    db: AsyncSession,
    firebase_uid: str,
    claims: dict,
) -> User:
    """
    Find existing user by firebase_uid or create a new one.
    Updates email / display_name / photo_url and last_seen_at on every login.
    """
    result = await db.execute(
        select(User).where(User.firebase_uid == firebase_uid)
    )
    user = result.scalar_one_or_none()

    email = claims.get("email")
    display_name = claims.get("name")
    photo_url = claims.get("picture")
    now = datetime.now(timezone.utc)

    if user is None:
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            display_name=display_name,
            photo_url=photo_url,
        )
        db.add(user)
        logger.info("New user created: firebase_uid=%s email=%s", firebase_uid, email)
    else:
        user.email = email
        user.display_name = display_name
        user.photo_url = photo_url
        user.last_seen_at = now

    await db.flush() 
    return user
