"""
Document schemas — Pydantic models for API responses.
Handles presigned URL serialization (internal MinIO → external via nginx).
"""

from pydantic import BaseModel, field_serializer
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.config.settings import settings


class BboxRef(BaseModel):
    """A bounding box reference on a specific page."""
    page: int
    bbox: List[float]


class Citation(BaseModel):
    """Citation pointing to a specific region in the original document."""
    node_id: str
    title: str
    pages: List[int]
    bboxes: List[BboxRef]
    source_url: str  # presigned MinIO URL

    @field_serializer("source_url")
    def serialize_source_url(self, url: str, _info) -> str:
        """
        Convert internal MinIO URL to external URL.
        Internal: http://minio:9000/documents/... (docker network)
        External: http://localhost:29000/documents/... (nginx proxy)

        In production, nginx reverse proxy handles:
          external:29000 → minio:9000
        """
        # Replace internal MinIO endpoint with external URL
        internal = f"http://{settings.minio_endpoint}"
        external = settings.minio_external_url
        if internal != external and internal in url:
            return url.replace(internal, external)
        return url


class DocumentResponse(BaseModel):
    doc_id: str
    file_name: str
    minio_key: str
    status: str
    node_count: int = 0
    created_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


class RetrievalResponse(BaseModel):
    """Response from reasoning-based retrieval."""
    answer: str
    citations: List[Citation]
    doc_id: str


class DocumentUploadResponse(BaseModel):
    doc_id: str
    minio_key: str
    status: str
    message: str
