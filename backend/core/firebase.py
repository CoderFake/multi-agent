"""
core/firebase.py — Firebase Admin SDK initialization + token verification.
Loaded lazily on first use — no crash if credentials not yet filled in .env.
"""
import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_firebase_app():
    """Initialize and cache the Firebase Admin app from settings."""
    import firebase_admin
    from firebase_admin import credentials

    from core.config import settings

    if firebase_admin._apps:
        return firebase_admin.get_app()

    cred_dict = {
        "type": settings.firebase_type,
        "project_id": settings.firebase_project_id,
        "private_key_id": settings.firebase_private_key_id,
        "private_key": settings.firebase_private_key.replace("\\n", "\n"),
        "client_email": settings.firebase_client_email,
        "client_id": settings.firebase_client_id,
        "auth_uri": settings.firebase_auth_uri,
        "token_uri": settings.firebase_token_uri,
    }

    cred = credentials.Certificate(cred_dict)
    app = firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin initialized for project: %s", settings.firebase_project_id)
    return app


def verify_id_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token and return the decoded claims.
    Raises ValueError on invalid/expired token.
    """
    from firebase_admin import auth

    _get_firebase_app()  # ensure initialized

    try:
        decoded = auth.verify_id_token(id_token)
        return decoded
    except Exception as e:
        raise ValueError(f"Invalid Firebase token: {e}") from e


def get_uid(id_token: str) -> str:
    """Verify token and return the user's Firebase UID."""
    claims = verify_id_token(id_token)
    return claims["uid"]
