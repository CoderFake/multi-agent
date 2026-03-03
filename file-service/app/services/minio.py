"""
Async MinIO service — upload, delete, presigned URL generation.
Uses miniopy-async for non-blocking I/O.

Presigned URLs use the INTERNAL MinIO endpoint (minio:9000 in Docker).
Nginx reverse proxy converts external requests:
  http(s)://external:29000/... → http://minio:9000/...
Schema serializers handle URL rewriting in responses.
"""

import io
import logging
from datetime import timedelta

from miniopy_async import Minio

from app.config.settings import settings

logger = logging.getLogger(__name__)


class MinioService:
    """Async MinIO singleton."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
            cls._instance._bucket_ready = False
        return cls._instance

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
        return self._client

    async def _ensure_bucket(self):
        if not self._bucket_ready:
            if not await self.client.bucket_exists(settings.minio_bucket):
                await self.client.make_bucket(settings.minio_bucket)
                logger.info("Created MinIO bucket: %s", settings.minio_bucket)
            self._bucket_ready = True

    async def upload_bytes(
        self, object_key: str, data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload raw bytes to MinIO. Returns object_key."""
        await self._ensure_bucket()
        await self.client.put_object(
            settings.minio_bucket,
            object_key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.info("Uploaded: %s/%s (%d bytes)", settings.minio_bucket, object_key, len(data))
        return object_key

    async def upload_file(self, object_key: str, file_path: str) -> str:
        """Upload a local file to MinIO."""
        await self._ensure_bucket()
        await self.client.fput_object(settings.minio_bucket, object_key, file_path)
        logger.info("Uploaded file: %s/%s", settings.minio_bucket, object_key)
        return object_key

    async def get_presigned_url(self, object_key: str, expires_hours: int = 24) -> str:
        """
        Generate presigned URL using INTERNAL MinIO endpoint.
        Nginx handles external→internal URL rewriting.
        """
        url = await self.client.presigned_get_object(
            settings.minio_bucket,
            object_key,
            expires=timedelta(hours=expires_hours),
        )
        return url

    async def delete_object(self, object_key: str):
        """Delete an object from MinIO."""
        await self.client.remove_object(settings.minio_bucket, object_key)
        logger.info("Deleted: %s/%s", settings.minio_bucket, object_key)


minio_service = MinioService()
