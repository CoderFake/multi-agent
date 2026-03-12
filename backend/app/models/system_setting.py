"""
CMS System Setting model.
"""
import uuid
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class CmsSystemSetting(Base):
    """System-level key-value configuration."""
    __tablename__ = "cms_system_setting"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSONB, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<CmsSystemSetting(key={self.key})>"
