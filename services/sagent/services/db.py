"""Shared database access for backend services.

Backward-compatible re-export from core.database.
New code should import directly from core.database.

Usage:
    from core.database import get_session  # preferred
    from services.db import get_session     # legacy
"""

from core.database import Base, get_session, init_db

__all__ = ["Base", "get_session", "init_db"]
