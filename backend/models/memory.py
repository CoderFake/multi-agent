"""
models/memory.py — SQLAlchemy ORM model for user memories.

Stores each memory fact extracted by Mem0 so we can query them
directly via SQLAlchemy (fast get_all, filter by user, paginate)
without going through Mem0's internal API on every listing request.

Schema mirrors what Mem0 stores internally, plus our UUIDv7 user FK.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, DateTime, Float, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Memory(Base):
    __tablename__ = "memories"

    # mem0's own memory ID (string UUID from mem0)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # FK → users.id (our UUIDv7 internal PK)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The extracted fact / instruction / preference text
    memory: Mapped[str] = mapped_column(Text, nullable=False)

    # Relevance score (populated during search, null for listing)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Categories / tags (comma-separated — kept simple for now)
    categories: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship back to User
    user = relationship("User", back_populates="memories")

    def to_dict(self) -> dict:
        cats = [c.strip() for c in self.categories.split(",")] if self.categories else []
        return {
            "id": self.id,
            "memory": self.memory,
            "score": self.score,
            "categories": cats,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Memory id={self.id} user_id={self.user_id}>"


# Extra index for temporal queries
Index("idx_memories_user_created", Memory.user_id, Memory.created_at.desc())
