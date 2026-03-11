"""Index route — document ingestion."""

from fastapi import APIRouter, HTTPException

from app.schemas.common import ErrorResponse
from app.schemas.index import IndexRequest, IndexResponse
from app.services.index_service import index_svc

router = APIRouter(prefix="/api/v1")


@router.post(
    "/index",
    response_model=IndexResponse,
    responses={500: {"model": ErrorResponse, "description": "Indexing failed"}},
    summary="Index document chunks",
    description=(
        "Embed and store document chunks into a Milvus collection. "
        "Called via internal webhook or RabbitMQ worker."
    ),
)
async def index_documents(request: IndexRequest):
    try:
        return await index_svc.index_documents(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}") from e

