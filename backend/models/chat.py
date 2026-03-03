"""
models/chat.py — ChatSession & ChatMessage models.

ChatSession: groups messages by conversation.
ChatMessage: a single row holds both query (user) and response (assistant).
"""
from datetime import datetime, timezone
from typing import List, Optional

from uuid6 import uuid7
from sqlalchemy import String, Text, DateTime, ForeignKey, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid7())
    )

    # FK → users.id
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional title (auto-generated from first message, or user-set)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="chat_sessions"
    )
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.order.asc()",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} title={self.title}>"


class ChatMessage(Base):
    """
    Each row = one query + response pair.
    - query:    the user's message
    - response: the assistant's reply
    """
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid7())
    )

    # FK → chat_sessions.id
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Message order within the session (1, 2, 3, ...)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # User's query
    query: Mapped[str] = mapped_column(Text, nullable=False)

    # Assistant's response (nullable — may be pending)
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship back to session
    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} order={self.order}>"
