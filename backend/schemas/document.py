from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    doc_id: str
    status: str


class DocumentStatusResponse(BaseModel):
    doc_id: str
    file_name: str
    status: str
    engine: str
    page_count: int


class DocumentListItem(BaseModel):
    doc_id: str
    file_name: str
    status: str
    engine: str
    page_count: int
    created_at: str


class DeleteResponse(BaseModel):
    deleted: bool
