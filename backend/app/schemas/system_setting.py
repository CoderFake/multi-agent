"""
System settings schemas — request/response models.
"""
from typing import Any, Optional
from pydantic import BaseModel


class SettingResponse(BaseModel):
    """System setting response."""
    id: str
    key: str
    value: Any
    description: Optional[str] = None

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    """PUT /system/settings/{key}."""
    value: Any
    description: Optional[str] = None
