"""
Feedback schemas — create + response models for API.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """Feedback creation — category + message (images via multipart)."""
    category: str = Field(..., pattern="^(bug|feature_request|question|other)$")
    message: str = Field(..., min_length=1, max_length=10000)


class FeedbackResponse(BaseModel):
    """Single feedback item."""
    id: str
    user_id: str
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    category: str
    message: str
    attachments: Optional[list[str]] = None  # public URLs
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackListResponse(BaseModel):
    """Paginated feedback list."""
    items: list[FeedbackResponse]
    total: int
    page: int
    page_size: int


class FeedbackStatusUpdate(BaseModel):
    """Update feedback status."""
    status: str = Field(..., pattern="^(new|reviewed|resolved)$")
