"""Search request/response schemas."""

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    """Vector similarity search across one or more Milvus collections."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language search query",
        examples=["How to configure OAuth2 in FastAPI?"],
    )
    collection_names: list[str] = Field(
        ...,
        min_length=1,
        description="Milvus collection names to search",
        examples=[["team_engineering", "team_docs"]],
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return",
    )

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query must not be blank")
        return v.strip()

    @field_validator("collection_names")
    @classmethod
    def collection_names_not_empty(cls, v: list[str]) -> list[str]:
        cleaned = [name.strip() for name in v if name.strip()]
        if not cleaned:
            raise ValueError("At least one collection name is required")
        return cleaned

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "authentication best practices",
                    "collection_names": ["team_engineering"],
                    "top_k": 5,
                }
            ]
        }
    }


class SearchResult(BaseModel):
    """A single search result with relevance score."""

    text: str = Field(..., description="Matched document chunk text")
    source: str = Field(..., description="Source identifier (file path or URL)")
    score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score (0-1)")
    file_name: str = Field(default="", description="Original file name")
    chunk_index: int = Field(default=0, ge=0, description="Position of this chunk in the source document")


class SearchResponse(BaseModel):
    """Search response containing ranked results."""

    results: list[SearchResult] = Field(default_factory=list, description="Ranked search results")
    total: int = Field(..., ge=0, description="Total number of results returned")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "results": [
                        {
                            "text": "Use OAuth2 with Password flow for simple auth...",
                            "source": "docs/auth.md",
                            "score": 0.92,
                            "file_name": "auth.md",
                            "chunk_index": 3,
                        }
                    ],
                    "total": 1,
                }
            ]
        }
    }

