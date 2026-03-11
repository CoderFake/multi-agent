"""File listing route."""

from fastapi import APIRouter, HTTPException

from app.schemas.common import ErrorResponse
from app.schemas.files import ListFilesRequest, ListFilesResponse
from app.services.file_service import file_svc

router = APIRouter(prefix="/api/v1")


@router.post(
    "/files",
    response_model=ListFilesResponse,
    responses={500: {"model": ErrorResponse, "description": "File listing failed"}},
    summary="List indexed files",
    description="List distinct indexed files across one or more Milvus collections.",
)
async def list_files(request: ListFilesRequest):
    try:
        return await file_svc.list_files(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File listing failed: {e}") from e

