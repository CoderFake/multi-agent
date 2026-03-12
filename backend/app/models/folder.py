"""
CMS Folder model — hierarchical folder tree for knowledge base.
"""
import uuid
from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class CmsFolder(Base):
    """Folder tree for organizing documents within an org."""
    __tablename__ = "cms_folder"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_folder.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    access_type = Column(String(20), default="public", nullable=False)  # public, restricted
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<CmsFolder(name={self.name})>"
