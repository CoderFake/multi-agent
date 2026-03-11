"""Database engine, session factory, and declarative base.

Sagent is a **service layer** — it reads and writes data but does NOT manage
the database schema. Schema is owned entirely by Drizzle (web/src/lib/schema.ts).
ADK manages its own session/event tables internally on startup.

Usage:
    from core.database import Base, get_session
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import settings

# ── Lazy singletons ──────────────────────────────────────────────────────
_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


def get_engine():
    """Get or create the database engine with production-grade pooling.

    Pool configuration:
    - pool_pre_ping: Validates connections before use (handles Cloud SQL restarts)
    - pool_size: Base connections to maintain (Cloud Run scales instances)
    - max_overflow: Additional connections under load
    - pool_recycle: Recreate connections after 30 min (Cloud SQL proxy timeout)
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
        )
    return _engine


def get_session():
    """Get a new synchronous database session.

    Usage:
        session = get_session()
        try:
            result = session.query(UserTeam).filter_by(user_id=uid).all()
        finally:
            session.close()
    """
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()



