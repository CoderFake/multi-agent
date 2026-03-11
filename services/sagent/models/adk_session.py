"""Read-only ORM model for ADK's sessions table.

This model maps to the table created and managed by google-adk's
DatabaseSessionService. It is used ONLY for read queries (e.g. title
retrieval) — never for writes. ADK owns this table.

The model uses ``__table_args__ = {"extend_existing": True}`` so it
won't conflict if ADK has already reflected / created the table.
"""

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class AdkSession(Base):
    """Read-only mapping of ADK's ``sessions`` table.

    Only the columns needed for application queries are mapped here.
    """

    __tablename__ = "sessions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String, primary_key=True)
    app_name: Mapped[str] = mapped_column(String)
    user_id: Mapped[str] = mapped_column(String)
    state: Mapped[dict | None] = mapped_column(JSONB)

