"""Backward-compatible re-export from core.database.

All new code should import directly from core.database:
    from core.database import Base, get_session
"""

from core.database import Base, get_engine, get_session

__all__ = ["Base", "get_engine", "get_session"]

