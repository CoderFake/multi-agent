"""
System settings schemas — request/response models.
"""
from typing import Any, Optional
from pydantic import BaseModel

from app.schemas.common import CmsBaseSchema, StrUUID


class SettingResponse(CmsBaseSchema):
    """System setting response."""
    id: StrUUID
    key: str
    value: Any
    description: Optional[str] = None


class SettingUpdate(BaseModel):
    """PUT /system/settings/{key}."""
    value: Any
    description: Optional[str] = None
