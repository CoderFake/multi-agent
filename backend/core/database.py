"""
core/database.py — SQLAlchemy async engine + session factory.
Connects to the same PostgreSQL used by mem0 / pgvector.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import settings


def _build_dsn() -> str:
    return (
        f"postgresql+asyncpg://{settings.mem0_pg_user}:{settings.mem0_pg_password}"
        f"@{settings.mem0_pg_host}:{settings.mem0_pg_port}/{settings.mem0_pg_db}"
    )


engine = create_async_engine(
    _build_dsn(),
    pool_size=10,
    max_overflow=20,
    echo=False,          # set True to log SQL in dev
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def init_db() -> None:
    """Create all tables (idempotent — does nothing if tables exist)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for DB sessions (use in non-FastAPI code)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an AsyncSession per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
