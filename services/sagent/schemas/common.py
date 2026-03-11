"""Shared base schemas — error responses, success wrappers."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response returned on failure.

    Displayed in Swagger UI for 4xx/5xx responses.
    """

    error: str = Field(
        ...,
        description="Human-readable error message",
        examples=["Session not found"],
    )

    model_config = {"json_schema_extra": {"examples": [{"error": "Session not found"}]}}


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = Field(default=True, description="Whether the operation succeeded")
    error: str | None = Field(default=None, description="Error message if success is False")

    model_config = {"json_schema_extra": {"examples": [{"success": True}]}}

