"""
Knowledge schemas — request/response models for folders, documents, and agent knowledge sources.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import CmsBaseSchema, StrUUID


# ── Folder ───────────────────────────────────────────────────────────────

class FolderCreate(BaseModel):
    """POST /tenant/knowledge/folders."""
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    access_type: str = "public"  # public, restricted


class FolderUpdate(BaseModel):
    """PUT /tenant/knowledge/folders/{id}."""
    name: Optional[str] = None
    description: Optional[str] = None
    access_type: Optional[str] = None
    sort_order: Optional[int] = None


class FolderResponse(CmsBaseSchema):
    """Folder response."""
    id: StrUUID
    org_id: StrUUID
    parent_id: Optional[StrUUID] = None
    name: str
    description: Optional[str] = None
    access_type: str
    sort_order: int
    created_at: datetime
    document_count: int = 0
    children: list["FolderResponse"] = []


# ── Document ─────────────────────────────────────────────────────────────

class DocumentUpload(BaseModel):
    """Document metadata (file uploaded via multipart)."""
    title: str
    folder_id: str


class DocumentResponse(CmsBaseSchema):
    """Document response."""
    id: StrUUID
    org_id: StrUUID
    folder_id: StrUUID
    uploaded_by: Optional[StrUUID] = None
    title: str
    file_name: str
    file_type: str
    file_size: int
    access_type: str
    index_status: str
    chunk_count: int
    indexed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class DocumentListResponse(BaseModel):
    """Paginated document list."""
    items: list[DocumentResponse]
    total: int


# ── Document Access ──────────────────────────────────────────────────────

class DocumentAccessCreate(BaseModel):
    """Assign group access to folder/document."""
    group_id: str
    can_read: bool = True
    can_write: bool = False


# ── Agent Knowledge Source ───────────────────────────────────────────────

class AgentKnowledgeCreate(BaseModel):
    """Link agent to folder/document as knowledge source."""
    agent_id: str
    folder_id: Optional[str] = None
    document_id: Optional[str] = None


class AgentKnowledgeResponse(CmsBaseSchema):
    """Agent ↔ knowledge source response."""
    id: StrUUID
    org_id: StrUUID
    agent_id: StrUUID
    folder_id: Optional[StrUUID] = None
    document_id: Optional[StrUUID] = None
    created_at: datetime
