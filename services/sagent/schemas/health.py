"""Health check response schema."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy", description="Service health status")
    agent: str = Field(..., description="Root agent name")

    model_config = {
        "json_schema_extra": {
            "examples": [{"status": "healthy", "agent": "root_agent"}]
        }
    }

