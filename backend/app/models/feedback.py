"""
CmsFeedback model — user feedback with optional image attachments.
"""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.models.base import Base


class CmsFeedback(Base):
    """User feedback — bug reports, feature requests, questions."""
    __tablename__ = "cms_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("cms_user.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("cms_organization.id", ondelete="CASCADE"), nullable=True)
    category = Column(String(30), nullable=False)  # bug, feature_request, question, other
    message = Column(Text, nullable=False)
    attachments = Column(JSONB, nullable=True)  # list of S3 paths ["feedback/{id}/img1.png", ...]
    status = Column(String(20), default="new", nullable=False)  # new, reviewed, resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_feedback_user", "user_id"),
        Index("ix_feedback_org", "org_id"),
        Index("ix_feedback_status", "status"),
        Index("ix_feedback_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<CmsFeedback(id={self.id}, category={self.category}, user_id={self.user_id})>"
