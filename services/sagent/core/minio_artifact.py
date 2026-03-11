"""MinIO-backed artifact service for ADK.

S3-compatible replacement for GcsArtifactService.
Stores artifacts in MinIO with versioning via key naming convention:
    {app_name}/{user_id}/{session_id}/{filename}/{version}

Usage:
    from core.minio_artifact import MinioArtifactService

    svc = MinioArtifactService(
        endpoint="minio:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        bucket="agent-artifacts",
    )
"""

import io
import json
import logging
from typing import Any, Optional, Union

from google.adk.artifacts.base_artifact_service import ArtifactVersion, BaseArtifactService
from google.genai import types
from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


class MinioArtifactService(BaseArtifactService):
    """Artifact service backed by MinIO (S3-compatible)."""

    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self._bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
                logger.info(f"Created MinIO bucket: {self._bucket}")
        except S3Error as e:
            logger.error(f"Failed to ensure bucket '{self._bucket}': {e}")

    def _prefix(
        self,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
    ) -> str:
        """Build the object key prefix."""
        if session_id:
            return f"{app_name}/{user_id}/{session_id}/{filename}"
        return f"{app_name}/{user_id}/{filename}"

    def _get_latest_version(self, prefix: str) -> int:
        """Get the latest version number for a given prefix. Returns -1 if none."""
        max_version = -1
        objects = self._client.list_objects(self._bucket, prefix=f"{prefix}/")
        for obj in objects:
            try:
                ver = int(obj.object_name.rsplit("/", 1)[-1])
                max_version = max(max_version, ver)
            except (ValueError, IndexError):
                continue
        return max_version

    async def save_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        artifact: types.Part,
        session_id: Optional[str] = None,
        custom_metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        """Save artifact to MinIO. Returns version number (0-based)."""
        prefix = self._prefix(app_name, user_id, filename, session_id)
        version = self._get_latest_version(prefix) + 1
        key = f"{prefix}/{version}"

        # Serialize Part to JSON bytes
        data = artifact.model_dump_json().encode("utf-8")

        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type="application/json",
            metadata=custom_metadata or {},
        )

        logger.debug(f"Saved artifact: {key} ({len(data)} bytes)")
        return version

    async def load_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Optional[types.Part]:
        """Load artifact from MinIO."""
        prefix = self._prefix(app_name, user_id, filename, session_id)

        if version is None:
            version = self._get_latest_version(prefix)
            if version < 0:
                return None

        key = f"{prefix}/{version}"

        try:
            response = self._client.get_object(self._bucket, key)
            data = json.loads(response.read())
            response.close()
            response.release_conn()
            return types.Part.model_validate(data)
        except S3Error:
            return None

    async def list_artifact_keys(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> list[str]:
        """List all artifact filenames for a user/session."""
        if session_id:
            prefix = f"{app_name}/{user_id}/{session_id}/"
        else:
            prefix = f"{app_name}/{user_id}/"

        keys: set[str] = set()
        objects = self._client.list_objects(self._bucket, prefix=prefix, recursive=True)
        for obj in objects:
            relative = obj.object_name[len(prefix):]
            parts = relative.rsplit("/", 1)
            if len(parts) == 2:
                keys.add(parts[0])
        return sorted(keys)

    async def delete_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
    ) -> None:
        """Delete all versions of an artifact from MinIO."""
        prefix = self._prefix(app_name, user_id, filename, session_id)
        objects = self._client.list_objects(self._bucket, prefix=f"{prefix}/")
        for obj in objects:
            self._client.remove_object(self._bucket, obj.object_name)
        logger.debug(f"Deleted artifact: {prefix}")

    async def list_versions(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
    ) -> list[int]:
        """Lists all versions of an artifact."""
        prefix = self._prefix(app_name, user_id, filename, session_id)
        versions = []
        objects = self._client.list_objects(self._bucket, prefix=f"{prefix}/")
        for obj in objects:
            try:
                ver = int(obj.object_name.rsplit("/", 1)[-1])
                versions.append(ver)
            except (ValueError, IndexError):
                continue
        return sorted(versions)

    async def get_artifact_version(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Optional[ArtifactVersion]:
        """Gets the metadata for a specific version of an artifact."""
        prefix = self._prefix(app_name, user_id, filename, session_id)
        if version is None:
            version = self._get_latest_version(prefix)
            if version < 0:
                return None
        
        key = f"{prefix}/{version}"
        try:
            stat = self._client.stat_object(self._bucket, key)
            return ArtifactVersion(
                version=version,
                canonical_uri=f"minio://{self._bucket}/{key}",
                custom_metadata=stat.metadata or {},
                create_time=stat.last_modified.timestamp() if stat.last_modified else 0,
                mime_type=stat.content_type
            )
        except S3Error:
            return None

    async def list_artifact_versions(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
    ) -> list[ArtifactVersion]:
        """Lists all versions and their metadata for a specific artifact."""
        versions = await self.list_versions(
            app_name=app_name, user_id=user_id, filename=filename, session_id=session_id
        )
        results = []
        for v in versions:
            meta = await self.get_artifact_version(
                app_name=app_name, user_id=user_id, filename=filename, session_id=session_id, version=v
            )
            if meta:
                results.append(meta)
        return results
