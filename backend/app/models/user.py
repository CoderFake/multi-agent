"""
CMS User and Invite models — authentication and invite-based registration.
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class CmsUser(Base, TimestampMixin, SoftDeleteMixin):
    """User account for CMS backend."""
    __tablename__ = "cms_user"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False, index=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    avatar_url = Column(String(500), nullable=True)  # S3 storage path

    def __repr__(self) -> str:
        return f"<CmsUser(id={self.id}, email={self.email})>"


class CmsInvite(Base, TimestampMixin):
    """Invite-based registration: admin invites user → email with token + temp password."""
    __tablename__ = "cms_invite"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    token = Column(Text, unique=True, nullable=False, index=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("cms_organization.id", ondelete="CASCADE"), nullable=False, index=True)
    org_role = Column(String(20), nullable=False)  # OrgRole value
    invited_by = Column(UUID(as_uuid=True), ForeignKey("cms_user.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending, accepted, expired, revoked
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<CmsInvite(email={self.email}, status={self.status})>"
