"""
CMS Document models — documents, access control, agent knowledge, and indexing jobs.
"""
import uuid
from sqlalchemy import Column, String, Boolean, Integer, BigInteger, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin


class CmsDocument(Base, TimestampMixin):
    """Uploaded document (file) within a folder."""
    __tablename__ = "cms_document"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    folder_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_folder.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    title = Column(String(500), nullable=False)
    file_name = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf, docx, txt, md
    file_size = Column(BigInteger, default=0, nullable=False)
    storage_path = Column(String(1000), nullable=False)  # MinIO path
    access_type = Column(String(20), default="public", nullable=False)  # public, restricted
    index_status = Column(String(20), default="pending", nullable=False, index=True)  # pending, indexing, indexed, failed
    chunk_count = Column(Integer, default=0, nullable=False)
    indexed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<CmsDocument(title={self.title})>"


class CmsDocumentAccess(Base):
    """Group-based access control for documents and folders."""
    __tablename__ = "cms_document_access"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("cms_document.id", ondelete="CASCADE"), nullable=True, index=True)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("cms_folder.id", ondelete="CASCADE"), nullable=True, index=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("cms_group.id", ondelete="CASCADE"), nullable=False, index=True)
    can_read = Column(Boolean, default=True, nullable=False)
    can_write = Column(Boolean, default=False, nullable=False)


class CmsAgentKnowledge(Base):
    """Agent ↔ folder/document knowledge source mapping."""
    __tablename__ = "cms_agent_knowledge"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("cms_organization.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("cms_agent.id", ondelete="CASCADE"), nullable=False, index=True)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("cms_folder.id", ondelete="CASCADE"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("cms_document.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)


class CmsKnowledgeIndexJob(Base):
    """Tracking Milvus indexing jobs for documents."""
    __tablename__ = "cms_knowledge_index_job"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("cms_organization.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("cms_document.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending, processing, completed, failed
    total_chunks = Column(Integer, default=0, nullable=False)
    processed_chunks = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
