"""
CMS OAuth Connection model.
"""
import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, TimestampMixin


class CmsOAuthConnection(Base, TimestampMixin):
    """OAuth tokens per user per org (e.g. Google, GitHub)."""
    __tablename__ = "cms_oauth_connection"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("cms_user.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("cms_organization.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(String(500), nullable=True)
    provider_account_id = Column(String(255), nullable=True)
    extra_data = Column(JSONB, nullable=True)
