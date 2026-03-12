"""
Common response schemas shared across all endpoints.
"""
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


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
