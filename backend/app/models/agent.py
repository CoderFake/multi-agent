"""
CMS Agent and Org-Agent models.
"""
import uuid
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class CmsAgent(Base):
    """
    Agent registry. org_id=NULL → system agent, org_id set → tenant agent.
    """
    __tablename__ = "cms_agent"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("cms_organization.id", ondelete="CASCADE"), nullable=True, index=True)
    codename = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    default_config = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<CmsAgent(codename={self.codename})>"


class CmsOrgAgent(Base):
    """Org enable/disable a system agent, with optional config override."""
    __tablename__ = "cms_org_agent"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_agent.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_enabled = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)  # True → bypass group check
    config_override = Column(JSONB, nullable=True)
