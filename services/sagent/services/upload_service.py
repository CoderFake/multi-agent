"""Upload business logic — validate, convert, and store file artifacts.

Usage:
    from services.upload_service import upload_svc

    result = await upload_svc.process_upload(file, session_id, user_id)
"""

import logging

from google.genai import types

from common.constants import APP_NAME
from converters import convert_file, needs_conversion
from converters.base import ConversionError
from core.dependencies import artifact_service
from utils.upload_limits import (
    MAX_FILE_SIZE_BYTES,
    get_supported_types_list,
    is_supported_mime_type,
)

logger = logging.getLogger(__name__)


class UploadError(Exception):
    """Base upload error with HTTP-friendly attributes."""

    def __init__(self, status_code: int, detail: dict):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail.get("message", "Upload error"))


class UploadService:
    """Business logic for file upload and artifact storage."""

    async def process_upload(
        self,
        file_bytes: bytes,
        content_type: str,
        filename: str,
        session_id: str,
        user_id: str,
    ) -> dict:
        """Validate, convert if needed, and store a file as an ADK artifact.

        Args:
            file_bytes: Raw file content.
            content_type: MIME type of the file.
            filename: Original filename.
            session_id: Current chat session ID.
            user_id: User identifier.

        Returns:
            Artifact metadata dict.

        Raises:
            UploadError: On validation or storage failure.
        """
        # Validate MIME type
        if not is_supported_mime_type(content_type):
            raise UploadError(
                status_code=415,
                detail={
                    "error": "unsupported_file_type",
                    "message": f"File type '{content_type}' is not supported",
                    "supported_types": get_supported_types_list(),
                },
            )

        # Validate file size
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise UploadError(
                status_code=413,
                detail={
                    "error": "file_too_large",
                    "message": (
                        f"File size ({len(file_bytes)} bytes) exceeds "
                        f"limit ({MAX_FILE_SIZE_BYTES} bytes)"
                    ),
                    "max_size_bytes": MAX_FILE_SIZE_BYTES,
                },
            )

        # Convert non-native formats to Markdown
        original_filename = filename
        if needs_conversion(content_type):
            try:
                result = convert_file(file_bytes, content_type, filename)
                file_bytes = result.content
                content_type = result.mime_type
                filename = result.filename
                logger.info(f"Converted {original_filename} to {filename} ({content_type})")
            except ConversionError as e:
                raise UploadError(
                    status_code=422,
                    detail={
                        "error": "conversion_failed",
                        "message": f"Failed to convert file: {e}",
                    },
                ) from e

        # Store as ADK artifact
        artifact = types.Part.from_bytes(data=file_bytes, mime_type=content_type)

        try:
            version = await artifact_service.save_artifact(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
                filename=filename,
                artifact=artifact,
            )
        except Exception as e:
            logger.exception(f"Failed to save artifact {original_filename}: {e}")
            raise UploadError(
                status_code=500,
                detail={
                    "error": "storage_error",
                    "message": "Failed to store file",
                },
            ) from e

        logger.info(
            f"Saved artifact: {filename} v{version} for session {session_id}, "
            f"user_id: {user_id}"
        )

        return {
            "filename": filename,
            "original_filename": original_filename,
            "version": version,
            "mime_type": content_type,
            "size_bytes": len(file_bytes),
        }


# Module-level singleton
upload_svc = UploadService()

