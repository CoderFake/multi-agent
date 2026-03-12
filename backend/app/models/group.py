"""
CMS Group model — groups act as roles (no separate roles table).
Includes M2M association tables for user↔group, group↔permission, user↔permission.
"""
import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Table, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base

# ── M2M: User ↔ Group ──────────────────────────────────────────────────
cms_user_groups = Table(
    "cms_user_groups",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("cms_user.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", UUID(as_uuid=True), ForeignKey("cms_group.id", ondelete="CASCADE"), primary_key=True),
)

# ── M2M: Group ↔ Permission ────────────────────────────────────────────
cms_group_permissions = Table(
    "cms_group_permissions",
    Base.metadata,
    Column("group_id", UUID(as_uuid=True), ForeignKey("cms_group.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("cms_permission.id", ondelete="CASCADE"), primary_key=True),
)


class CmsGroup(Base):
    """
    Group = Role. System groups (org_id=NULL) are templates.
    Org groups (org_id set) are custom roles within that org.
    """
    __tablename__ = "cms_group"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("cms_organization.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_system_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<CmsGroup(id={self.id}, name={self.name})>"


class CmsUserPermission(Base):
    """Direct user↔permission override (grant or deny) within an org."""
    __tablename__ = "cms_user_permissions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("cms_user.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("cms_permission.id", ondelete="CASCADE"), primary_key=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("cms_organization.id", ondelete="CASCADE"), primary_key=True)
    is_granted = Column(Boolean, default=True, nullable=False)
