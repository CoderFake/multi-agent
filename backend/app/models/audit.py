"""
CMS Audit Log model.
"""
import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base
from app.utils.datetime_utils import now


class CmsAuditLog(Base):
    """Audit trail for all CMS actions."""
    __tablename__ = "cms_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("cms_user.id", ondelete="SET NULL"), nullable=True, index=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("cms_organization.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)

    def __repr__(self) -> str:
        return f"<CmsAuditLog(action={self.action}, resource={self.resource_type})>"
