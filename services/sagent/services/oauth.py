"""OAuth integration services.

Handles retrieving external provider tokens for agents.
"""

from typing import Optional

from sqlalchemy import select

from core.database import get_session
from models.oauth_connection import OAuthConnection


def get_oauth_connection(user_id: str, provider: str = "gitlab") -> Optional[OAuthConnection]:
    """Get the active OAuth connection for a user and provider.

    Args:
        user_id: The authenticated user's ID
        provider: The provider name (e.g., 'gitlab', 'google_drive')

    Returns:
        OAuthConnection if found and valid, None otherwise
    """
    session = get_session()
    try:
        stmt = select(OAuthConnection).where(
            OAuthConnection.user_id == user_id,
            OAuthConnection.provider == provider,
        )
        return session.execute(stmt).scalar_one_or_none()
    finally:
        session.close()
