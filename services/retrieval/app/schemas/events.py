"""Event schemas for indexing task progress.

Shared between retrieval service (writes) and backend (reads/SSE streams).
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of an indexing task."""
    QUEUED = "queued"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskEvent(BaseModel):
    """Progress event for an indexing task, stored in Redis."""
    job_id: str
    document_id: str = ""
    status: TaskStatus = TaskStatus.QUEUED
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""
    total_chunks: int = 0
    processed_chunks: int = 0
    error: Optional[str] = None
    updated_at: str = ""


class IndexTaskPayload(BaseModel):
    """Payload pushed to Redis idx:queue by backend."""
    job_id: str
    org_id: str
    org_subdomain: str
    document_id: str
    folder_id: str
    file_name: str
    storage_path: str
    access_type: str = "public"
    group_ids: list[str] = Field(default_factory=list)
    agent_code: str = ""
