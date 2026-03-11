"""Upload request/response schemas."""

from pydantic import BaseModel, Field


class UploadConfigResponse(BaseModel):
    """Upload constraints for frontend validation."""

    supported_types: list[str] = Field(
        ...,
        description="List of supported MIME types",
        examples=[["text/plain", "application/pdf", "text/markdown"]],
    )
    max_file_size_bytes: int = Field(
        ...,
        description="Maximum allowed file size in bytes",
        examples=[10485760],
    )
    max_files: int = Field(
        ...,
        description="Maximum files per upload batch",
        examples=[5],
    )


class UploadResponse(BaseModel):
    """Successful upload result."""

    filename: str = Field(..., description="Stored filename (may differ from original after conversion)")
    original_filename: str = Field(..., description="Original uploaded filename")
    version: int = Field(..., ge=0, description="Artifact version number")
    mime_type: str = Field(..., description="Final MIME type after conversion")
    size_bytes: int = Field(..., ge=0, description="Final file size in bytes")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "filename": "report.md",
                    "original_filename": "report.docx",
                    "version": 0,
                    "mime_type": "text/markdown",
                    "size_bytes": 4096,
                }
            ]
        }
    }


class UploadErrorDetail(BaseModel):
    """Structured upload error detail."""

    error: str = Field(..., description="Error code", examples=["unsupported_file_type"])
    message: str = Field(..., description="Human-readable error message")
    supported_types: list[str] | None = Field(default=None, description="Supported types (for 415 errors)")
    max_size_bytes: int | None = Field(default=None, description="Max size (for 413 errors)")

