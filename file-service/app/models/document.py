"""
Document ORM models — async SQLAlchemy mapped to PostgreSQL tables.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func  # noqa: F401
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    minio_key: Mapped[str] = mapped_column(String(512), nullable=False)
    bucket: Mapped[str] = mapped_column(String(128), default="documents")
    user_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="processing")
    engine: Mapped[str] = mapped_column(String(32), default="hybrid")        # which extractor
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    nodes: Mapped[List["DocumentNode"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    tree: Mapped[Optional["DocumentTree"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", uselist=False
    )


class DocumentTree(Base):
    __tablename__ = "document_trees"

    doc_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("documents.doc_id", ondelete="CASCADE"), primary_key=True
    )
    tree_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)

    document: Mapped["Document"] = relationship(back_populates="tree")


class DocumentNode(Base):
    __tablename__ = "document_nodes"

    node_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    doc_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("documents.doc_id", ondelete="CASCADE"), primary_key=True
    )
    parent_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    start_index: Mapped[int] = mapped_column(Integer, default=0)
    end_index: Mapped[int] = mapped_column(Integer, default=0)
    pages: Mapped[List[int]] = mapped_column(ARRAY(Integer), default=list)
    bboxes: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)

    document: Mapped["Document"] = relationship(back_populates="nodes")
