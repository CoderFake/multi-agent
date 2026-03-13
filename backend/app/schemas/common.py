"""
Common response schemas shared across all endpoints.
"""
from typing import Annotated, Any, Generic, Optional, TypeVar
from uuid import UUID
from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer

T = TypeVar("T")


def _coerce_uuid_to_str(v: Any) -> str:
    """Accept UUID or str, always return str."""
    if isinstance(v, UUID):
        return str(v)
    return str(v)


StrUUID = Annotated[
    str,
    BeforeValidator(_coerce_uuid_to_str),
]


class CmsBaseSchema(BaseModel):
    """Base schema for all CMS response models.

    Inherits from_attributes=True so SQLAlchemy ORM objects can be
    used directly as response data.
    """
    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Standard error response."""
    error_code: str
    detail: str
    status_code: int


class SuccessResponse(BaseModel):
    """Standard success response."""
    message: str
    data: Optional[Any] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
