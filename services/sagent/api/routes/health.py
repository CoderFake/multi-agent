"""Health check route."""

from fastapi import APIRouter

from agent import root_agent
from schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns service health and root agent name.",
)
async def health_check():
    """Health check endpoint for container orchestration."""
    return HealthResponse(status="healthy", agent=root_agent.name)

