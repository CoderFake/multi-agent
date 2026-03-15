"""
Indexing schemas — request/response models for knowledge indexing API.
"""
from typing import Optional

from pydantic import BaseModel, Field


class IndexJobSubmit(BaseModel):
    """Request to submit an indexing job for a document."""
    agent_code: str = Field(default="", description="Agent codename for collection naming")


class IndexJobResponse(BaseModel):
    """Response after submitting an indexing job."""
    job_id: str
    document_id: str
    status: str = "pending"
    message: str = "Job submitted"


class IndexJobProgress(BaseModel):
    """Progress of an indexing job (from Redis)."""
    job_id: str
    document_id: str = ""
    status: str = "queued"
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""
    total_chunks: int = 0
    processed_chunks: int = 0
    error: Optional[str] = None
    updated_at: str = ""


class ActiveJob(BaseModel):
    """Active indexing job info from DB."""
    id: str
    document_id: str
    status: str
    total_chunks: int = 0
    processed_chunks: int = 0
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    created_at: str
