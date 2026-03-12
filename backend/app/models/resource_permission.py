"""
CMS Resource Permission model — unified per-resource permission overrides.
"""
import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class CmsResourcePermission(Base):
    """
    Per-resource permission override.
    Can grant/deny a permission on a specific resource to a group or user.
    """
    __tablename__ = "cms_resource_permission"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    permission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_permission.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cms_organization.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_id = Column(UUID(as_uuid=True), ForeignKey("cms_group.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("cms_user.id", ondelete="CASCADE"), nullable=True)
    is_granted = Column(Boolean, default=True, nullable=False)
