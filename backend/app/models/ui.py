"""
CMS UI Component model.
"""
import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class CmsUIComponent(Base):
    """UI element registry (e.g. sidebar items, dashboard widgets)."""
    __tablename__ = "cms_ui_component"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codename = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    component_type = Column(String(100), nullable=False)

    def __repr__(self) -> str:
        return f"<CmsUIComponent(codename={self.codename})>"
