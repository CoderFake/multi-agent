"""
Notification schemas — i18n-based response models.
Frontend resolves title_code/message_code via locale files.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import CmsBaseSchema, StrUUID


class NotificationResponse(CmsBaseSchema):
    """Single notification."""
    id: StrUUID
    type: str
    title_code: str          # i18n key, e.g. "notification.role_changed"
    message_code: Optional[str] = None  # i18n key, e.g. "notification.role_changed_desc"
    data: Optional[dict] = None  # dynamic params for i18n interpolation
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated notification list."""
    items: list[NotificationResponse]
    total: int
    unread_count: int
