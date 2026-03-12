"""
CMS Organization and Membership models.
"""
import uuid
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, TimestampMixin
from app.common.enums import OrgRole


class CmsOrganization(Base, TimestampMixin):
    """Organization / Tenant."""
    __tablename__ = "cms_organization"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    subdomain = Column(String(100), unique=True, nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    description = Column(Text, nullable=True)
    settings = Column(JSONB, nullable=True)
    logo_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<CmsOrganization(id={self.id}, slug={self.slug})>"


class CmsOrgMembership(Base):
    """User ↔ Organization membership with role."""
    __tablename__ = "cms_org_membership"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_role = Column(String(20), default=OrgRole.MEMBER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<CmsOrgMembership(org={self.org_id}, user={self.user_id}, role={self.org_role})>"
