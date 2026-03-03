"""
models/user.py — User model with UUIDv7 internal PK + Firebase UID.

Flow:
  1. Firebase verifies ID token → firebase_uid (string)
  2. We look up / create a User row in PostgreSQL by firebase_uid
  3. Internal PK (id) is UUIDv7 — sortable, time-ordered UUID
"""
from datetime import datetime, timezone
from typing import List, Optional

from uuid6 import uuid7
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid7())
    )

    firebase_uid: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )

    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    # One user → many memories (cascade delete)
    memories: Mapped[List["Memory"]] = relationship(  # noqa: F821
        "Memory",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Memory.created_at.desc()",
        lazy="select",
    )

    # One user → many chat sessions
    chat_sessions: Mapped[List["ChatSession"]] = relationship(  # noqa: F821
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="ChatSession.updated_at.desc()",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
