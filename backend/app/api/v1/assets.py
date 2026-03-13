"""
Asset proxy endpoint — serves files from MinIO/S3 storage.

Local dev:  Backend proxies MinIO directly.
Production: Nginx can reverse-proxy /api/v1/assets/ → minio:9000
            (this endpoint still works as fallback).
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from minio.error import S3Error

from app.utils.storage import _get_client
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/{bucket}/{path:path}")
async def serve_asset(bucket: str, path: str):
    """
    Stream a file from MinIO storage.

    URL pattern: /api/v1/assets/{bucket}/{object_path}
    Example:     /api/v1/assets/nws/logo/d1ca21df1700.png
    """
    client = _get_client()

    try:
        response = client.get_object(bucket, path)
        content_type = response.headers.get("Content-Type", "application/octet-stream")

        return StreamingResponse(
            response.stream(32 * 1024),  # 32KB chunks
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",  # 24h browser cache
            },
        )
    except S3Error as e:
        if e.code == "NoSuchKey" or e.code == "NoSuchBucket":
            raise HTTPException(status_code=404, detail="File not found")
        logger.error(f"Failed to serve asset {bucket}/{path}: {e}")
        raise HTTPException(status_code=500, detail="Storage error")
