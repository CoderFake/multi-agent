"""Index (document ingestion) request/response schemas."""

from pydantic import BaseModel, Field, field_validator


class DocumentChunk(BaseModel):
    """A single document chunk to be embedded and indexed."""

    id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Unique chunk identifier",
        examples=["doc_abc123_chunk_0"],
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=65535,
        description="Chunk text content",
    )
    source: str = Field(
        ...,
        max_length=1024,
        description="Source path or URL",
        examples=["gs://bucket/docs/guide.md"],
    )
    file_name: str = Field(
        ...,
        max_length=512,
        description="Original file name",
        examples=["guide.md"],
    )
    chunk_index: int = Field(
        default=0,
        ge=0,
        description="Position of this chunk in the source document",
    )


class IndexRequest(BaseModel):
    """Request to embed and index document chunks into a Milvus collection."""

    collection_name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Target Milvus collection name",
        examples=["team_engineering"],
    )
    team_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Team identifier that owns this collection",
    )
    documents: list[DocumentChunk] = Field(
        ...,
        min_length=1,
        description="Document chunks to index",
    )

    @field_validator("collection_name")
    @classmethod
    def collection_name_valid(cls, v: str) -> str:
        v = v.strip()
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Collection name must be alphanumeric with underscores/hyphens only")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "collection_name": "team_engineering",
                    "team_id": "eng_001",
                    "documents": [
                        {
                            "id": "doc_abc_0",
                            "text": "FastAPI is a modern web framework...",
                            "source": "docs/intro.md",
                            "file_name": "intro.md",
                            "chunk_index": 0,
                        }
                    ],
                }
            ]
        }
    }


class IndexResponse(BaseModel):
    """Result of an indexing operation."""

    indexed: int = Field(..., ge=0, description="Number of chunks successfully indexed")
    collection_name: str = Field(..., description="Collection that received the chunks")

    model_config = {
        "json_schema_extra": {
            "examples": [{"indexed": 42, "collection_name": "team_engineering"}]
        }
    }

