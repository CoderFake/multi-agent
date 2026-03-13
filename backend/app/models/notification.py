"""
CmsNotification model — user notifications within an org.

Stores i18n codes (title_code, message_code) instead of hardcoded text.
Frontend resolves codes via locale files (e.g. t(`notification.${title_code}`)).
`data` carries dynamic params for interpolation (e.g. {role: "admin", group_name: "Editors"}).
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.models.base import Base


class CmsNotification(Base):
    """User notification — triggered by system events."""
    __tablename__ = "cms_notification"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("cms_user.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("cms_organization.id", ondelete="CASCADE"), nullable=True)
    type = Column(String(50), nullable=False, index=True)
    # i18n codes — frontend resolves via locale
    title_code = Column(String(100), nullable=False)  # e.g. "notification.role_changed"
    message_code = Column(String(100), nullable=True)  # e.g. "notification.role_changed_desc"
    data = Column(JSONB, nullable=True)  # dynamic params for i18n interpolation
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_notification_user_org", "user_id", "org_id"),
        Index("ix_notification_user_unread", "user_id", "is_read"),
        Index("ix_notification_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<CmsNotification(id={self.id}, type={self.type}, user_id={self.user_id})>"
