"""Pydantic schemas for the retrieval API.

Organized by domain. All models are re-exported here for convenience.

Usage:
    from app.schemas import SearchRequest, SearchResponse
"""

from app.schemas.common import ErrorResponse, PaginationParams
from app.schemas.files import FileInfo, ListFilesRequest, ListFilesResponse
from app.schemas.health import HealthResponse
from app.schemas.index import DocumentChunk, IndexRequest, IndexResponse
from app.schemas.search import SearchRequest, SearchResponse, SearchResult

__all__ = [
    # Common
    "ErrorResponse",
    "PaginationParams",
    # Search
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    # Index
    "IndexRequest",
    "IndexResponse",
    "DocumentChunk",
    # Files
    "ListFilesRequest",
    "ListFilesResponse",
    "FileInfo",
    # Health
    "HealthResponse",
]

