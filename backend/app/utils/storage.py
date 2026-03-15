"""
MinIO/S3 storage utility — upload, delete, URL mapping.

URL mapping logic:
- All public URLs route through /api/v1/assets/{bucket}/{path}
- Local dev: backend proxies to MinIO directly
- Production: nginx can reverse-proxy /api/v1/assets/ → minio:9000
"""
import io
import uuid
from typing import Optional

from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Singleton client — lazy init
_client: Optional[Minio] = None


def _get_client() -> Minio:
    """Get or create MinIO client singleton."""
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
    return _client


def _ensure_bucket(client: Minio, bucket: str) -> None:
    """Create bucket if it doesn't exist."""
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info(f"Created bucket: {bucket}")
    except S3Error as e:
        logger.error(f"Failed to ensure bucket {bucket}: {e}")


async def upload_file(
    file: UploadFile,
    path: str,
    bucket: Optional[str] = None,
) -> str:
    """
    Upload a file to MinIO.

    Args:
        file: FastAPI UploadFile
        path: Storage path inside bucket (e.g. "avatars/{user_id}/photo.jpg")
        bucket: Bucket name (defaults to settings.MINIO_BUCKET)

    Returns:
        The storage path (for saving in DB).
    """
    bucket = bucket or settings.MINIO_BUCKET
    client = _get_client()
    _ensure_bucket(client, bucket)

    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    try:
        client.put_object(
            bucket,
            path,
            io.BytesIO(content),
            length=len(content),
            content_type=content_type,
        )
        logger.info(f"Uploaded file: {bucket}/{path} ({len(content)} bytes)")
        return path
    except S3Error as e:
        logger.error(f"Failed to upload {path}: {e}")
        raise


async def upload_file_bytes(
    data: bytes,
    path: str,
    content_type: str = "application/octet-stream",
    bucket: Optional[str] = None,
) -> str:
    """
    Upload raw bytes to MinIO.

    Args:
        data: File content as bytes
        path: Storage path inside bucket
        content_type: MIME type
        bucket: Bucket name (defaults to settings.MINIO_BUCKET)

    Returns:
        The storage path (for saving in DB).
    """
    bucket = bucket or settings.MINIO_BUCKET
    client = _get_client()
    _ensure_bucket(client, bucket)

    try:
        client.put_object(
            bucket,
            path,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.info(f"Uploaded file: {bucket}/{path} ({len(data)} bytes)")
        return path
    except S3Error as e:
        logger.error(f"Failed to upload {path}: {e}")
        raise


async def delete_file(
    path: str,
    bucket: Optional[str] = None,
) -> bool:
    """Delete a file from MinIO."""
    bucket = bucket or settings.MINIO_BUCKET
    client = _get_client()

    try:
        client.remove_object(bucket, path)
        logger.info(f"Deleted file: {bucket}/{path}")
        return True
    except S3Error as e:
        logger.error(f"Failed to delete {path}: {e}")
        return False


def get_public_url(
    storage_path: Optional[str],
    bucket: Optional[str] = None,
) -> Optional[str]:
    """
    Convert internal storage path to public-facing URL via assets API.

    Returns a URL like: {CMS_API_BASE}/assets/{bucket}/{path}
    - Local dev:  http://localhost:8002/api/v1/assets/nws/logo/photo.jpg
    - Production: nginx can reverse-proxy /api/v1/assets/ to minio:9000

    Args:
        storage_path: Path stored in DB (e.g. "logo/uuid.jpg")
        bucket: Bucket name (defaults to settings.MINIO_BUCKET)

    Returns:
        Public URL string, or None if storage_path is None.
    """
    if not storage_path:
        return None

    bucket = bucket or settings.MINIO_BUCKET

    api_base = f"http://localhost:{settings.CMS_PORT}/api/v1"
    return f"{api_base}/assets/{bucket}/{storage_path}"


def generate_path(prefix: str, filename: str) -> str:
    """
    Generate a unique storage path.

    Args:
        prefix: Path prefix (e.g. "avatars/{user_id}", "feedback/{feedback_id}")
        filename: Original filename

    Returns:
        Unique path like "avatars/{user_id}/{uuid}_{filename}"
    """
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    unique_name = f"{uuid.uuid4().hex[:12]}.{ext}" if ext else uuid.uuid4().hex[:12]
    return f"{prefix}/{unique_name}"
