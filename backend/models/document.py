"""
models/document.py — Lightweight read-only ORM view of the `documents` table.

The documents table is owned + written by file-service.
Backend only needs to read it (list / status checks) so we map only the
columns we actually use; SQLAlchemy won't touch any columns we omit.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Document(Base):
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="processing")
    engine: Mapped[str] = mapped_column(String(32), default="hybrid")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
