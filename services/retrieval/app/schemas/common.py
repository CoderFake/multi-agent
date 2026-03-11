"""Shared base schemas — error responses, pagination, etc."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response returned on failure.

    Displayed in Swagger UI for 4xx/5xx responses.
    """

    detail: str = Field(..., description="Human-readable error message", examples=["Search failed: connection timeout"])

    model_config = {"json_schema_extra": {"examples": [{"detail": "Collection not found"}]}}


class PaginationParams(BaseModel):
    """Reusable pagination parameters."""

    limit: int = Field(default=50, ge=1, le=200, description="Max items to return")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")

