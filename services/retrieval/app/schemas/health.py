"""Health check response schema."""

from enum import Enum

from pydantic import BaseModel, Field


class ServiceStatus(str, Enum):
    """Service health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthResponse(BaseModel):
    """Health check response with dependency status."""

    status: ServiceStatus = Field(..., description="Overall service health")
    milvus: str = Field(..., description="Milvus connection status")
    version: str = Field(default="1.0.0", description="Service version")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"status": "healthy", "milvus": "connected", "version": "1.0.0"}
            ]
        }
    }

