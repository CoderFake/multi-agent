"""MinIO client for downloading files to process in the retrieval service.

Usage:
    from app.core.minio_client import download_file
"""

import logging
import os
from typing import Optional

from minio import Minio

from app.config.settings import settings

logger = logging.getLogger(__name__)

_client: Optional[Minio] = None


def get_minio() -> Minio:
    """Get or create MinIO client singleton."""
    global _client
    if _client is None:
        _client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        logger.info("MinIO connected: %s", settings.MINIO_ENDPOINT)
    return _client


def download_file(storage_path: str, dest_dir: str | None = None) -> str:
    """
    Download a file from MinIO to local temp directory.

    Returns the local file path.
    """
    client = get_minio()
    dest_dir = dest_dir or settings.TEMP_DIR
    os.makedirs(dest_dir, exist_ok=True)

    file_name = os.path.basename(storage_path)
    local_path = os.path.join(dest_dir, file_name)

    client.fget_object(settings.MINIO_BUCKET, storage_path, local_path)
    logger.info("Downloaded: %s → %s", storage_path, local_path)
    return local_path
