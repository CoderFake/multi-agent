"""Health check route."""

from fastapi import APIRouter

from app.core.milvus import get_milvus_client
from app.schemas.health import HealthResponse, ServiceStatus

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns service health and Milvus connection status.",
)
async def health_check():
    try:
        get_milvus_client()
        return HealthResponse(status=ServiceStatus.HEALTHY, milvus="connected")
    except Exception as e:
        return HealthResponse(status=ServiceStatus.DEGRADED, milvus=f"error: {e}")

