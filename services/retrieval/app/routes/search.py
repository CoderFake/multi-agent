"""Search route — vector similarity search."""

from fastapi import APIRouter, HTTPException

from app.schemas.common import ErrorResponse
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import search_svc

router = APIRouter(prefix="/api/v1")


@router.post(
    "/search",
    response_model=SearchResponse,
    responses={500: {"model": ErrorResponse, "description": "Search failed"}},
    summary="Vector similarity search",
    description=(
        "Search across one or more Milvus collections using natural language. "
        "Results are ranked by cosine similarity score."
    ),
)
async def search(request: SearchRequest):
    try:
        return await search_svc.search(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}") from e

