"""File upload routes."""

from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from schemas.upload import UploadConfigResponse, UploadResponse
from services.upload_service import UploadError, upload_svc
from utils.upload_limits import MAX_FILE_SIZE_BYTES, MAX_FILES, get_supported_types_list

router = APIRouter()


@router.get(
    "/api/upload/config",
    response_model=UploadConfigResponse,
    summary="Upload config",
    description="Return upload constraints for frontend validation.",
)
async def upload_config():
    """Return upload constraints for frontend validation.

    Single source of truth — frontend fetches this instead of duplicating constants.
    """
    return UploadConfigResponse(
        supported_types=get_supported_types_list(),
        max_file_size_bytes=MAX_FILE_SIZE_BYTES,
        max_files=MAX_FILES,
    )


@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={
        413: {"description": "File too large"},
        415: {"description": "Unsupported file type"},
        422: {"description": "Conversion failed"},
        500: {"description": "Storage error"},
    },
    summary="Upload file",
    description="Upload a file as an ADK artifact for use in chat.",
)
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Header(..., alias="x-session-id"),
    user_id: str = Header(..., alias="x-user-id"),
):
    """Upload a file as an ADK artifact for use in chat."""
    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"

    try:
        return await upload_svc.process_upload(
            file_bytes=file_bytes,
            content_type=content_type,
            filename=filename,
            session_id=session_id,
            user_id=user_id,
        )
    except UploadError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

