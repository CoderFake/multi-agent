"""File listing request/response schemas."""

from pydantic import BaseModel, Field, field_validator


class ListFilesRequest(BaseModel):
    """Request to list indexed files across collections."""

    collection_names: list[str] = Field(
        ...,
        min_length=1,
        description="Collections to list files from",
        examples=[["team_engineering"]],
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Max number of files to return",
    )

    @field_validator("collection_names")
    @classmethod
    def collection_names_not_empty(cls, v: list[str]) -> list[str]:
        cleaned = [name.strip() for name in v if name.strip()]
        if not cleaned:
            raise ValueError("At least one collection name is required")
        return cleaned


class FileInfo(BaseModel):
    """Metadata for an indexed file."""

    name: str = Field(..., description="File name")
    collection: str = Field(..., description="Collection the file belongs to")
    chunk_count: int = Field(default=0, ge=0, description="Number of indexed chunks for this file")


class ListFilesResponse(BaseModel):
    """Response containing indexed file metadata."""

    files: list[FileInfo] = Field(default_factory=list, description="Indexed files")
    total: int = Field(..., ge=0, description="Total files found")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "files": [
                        {"name": "guide.md", "collection": "team_engineering", "chunk_count": 12}
                    ],
                    "total": 1,
                }
            ]
        }
    }

