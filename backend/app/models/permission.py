"""
CMS Content Type and Permission models — Django-inspired permission system.
"""
import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class CmsContentType(Base):
    """Registry of resource types (like Django's ContentType)."""
    __tablename__ = "cms_content_type"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_label = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)

    def __repr__(self) -> str:
        return f"<CmsContentType({self.app_label}.{self.model})>"


class CmsPermission(Base):
    """Permission codenames linked to content types."""
    __tablename__ = "cms_permission"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_content_type.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    codename = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)

    def __repr__(self) -> str:
        return f"<CmsPermission({self.codename})>"
