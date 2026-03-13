"""
MinIO/S3 storage utility — upload, delete, URL mapping.

URL mapping logic:
- Docker: internal `http://minio:9000/bucket/path` → mapped to external URL
- Local dev: `http://localhost:9010/bucket/path`
- Production: `{origin}/storage/bucket/path` (nginx reverse-proxy handles `minio:9000`)

Backend always stores INTERNAL path (e.g. `avatars/{user_id}/photo.jpg`).
`get_public_url()` converts to external-facing URL based on request.
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
    request_origin: Optional[str] = None,
    bucket: Optional[str] = None,
) -> Optional[str]:
    """
    Convert internal storage path to public-facing URL.

    URL mapping:
    - If MINIO_PUBLIC_URL is set → use it directly (local dev / fixed config)
    - If request_origin is provided → use {origin}/storage/{bucket}/{path}
      (production: nginx proxies /storage/ to minio:9000)
    - Fallback → use MINIO_PUBLIC_URL from settings

    Args:
        storage_path: Path stored in DB (e.g. "avatars/uuid/photo.jpg")
        request_origin: Request origin (e.g. "https://app.example.com")
        bucket: Bucket name (defaults to settings.MINIO_BUCKET)

    Returns:
        Public URL string, or None if storage_path is None.
    """
    if not storage_path:
        return None

    bucket = bucket or settings.MINIO_BUCKET

    if request_origin:
        # Production: nginx reverse-proxy maps /storage/ → minio internal
        return f"{request_origin.rstrip('/')}/storage/{bucket}/{storage_path}"

    # Dev fallback: use configured public URL
    public_base = settings.MINIO_PUBLIC_URL.rstrip("/")
    return f"{public_base}/{bucket}/{storage_path}"


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
