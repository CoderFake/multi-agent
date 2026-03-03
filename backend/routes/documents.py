"""
Document REST API routes — bridges frontend ↔ backend gRPC ↔ file-service.

Endpoints:
  POST /api/documents/session          Upload + index a session document (gRPC → file-service)
  GET  /api/documents/{doc_id}/status  Check processing status (DB direct)
  POST /api/documents/knowledge        Upload to knowledge base (gRPC → file-service)
  GET  /api/documents/knowledge        List user's knowledge docs (DB direct)
  DELETE /api/documents/{doc_id}       Delete document (gRPC → file-service for MinIO + Milvus cleanup)
"""

from __future__ import annotations

import logging
from typing import List, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_user, validated_upload_file
from core.grpc_client import file_service_client
from models.document import Document
from models.user import User
from schemas.document import (
    DeleteResponse,
    DocumentListItem,
    DocumentStatusResponse,
    DocumentUploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


# ── Session document upload ────────────────────────────────────────────

@router.post("/session", response_model=DocumentUploadResponse)
async def upload_session_document(
    upload: Tuple[bytes, str] = Depends(validated_upload_file),
    current_user: User = Depends(get_current_user),
) -> DocumentUploadResponse:
    data, filename = upload
    try:
        result = await file_service_client.process_document(
            file_name=filename,
            file_data=data,
            user_id=current_user.id,
        )
    except Exception as e:
        logger.exception("Session document upload failed")
        raise HTTPException(status_code=500, detail=str(e))
    return DocumentUploadResponse(doc_id=result["doc_id"], status=result["status"])


# ── Document status (DB direct) ────────────────────────────────────────

@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentStatusResponse:
    doc = await db.get(Document, doc_id)
    if not doc or doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentStatusResponse(
        doc_id=doc.doc_id,
        file_name=doc.file_name,
        status=doc.status,
        engine=doc.engine,
        page_count=doc.page_count,
    )


# ── Knowledge base ─────────────────────────────────────────────────────

@router.post("/knowledge", response_model=DocumentUploadResponse)
async def upload_knowledge_document(
    upload: Tuple[bytes, str] = Depends(validated_upload_file),
    current_user: User = Depends(get_current_user),
) -> DocumentUploadResponse:
    data, filename = upload
    try:
        result = await file_service_client.process_document(
            file_name=filename,
            file_data=data,
            user_id=current_user.id,
        )
        return DocumentUploadResponse(doc_id=result["doc_id"], status=result["status"])
    except Exception as e:
        logger.exception("Knowledge document upload failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge", response_model=List[DocumentListItem])
async def list_knowledge_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentListItem]:
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        DocumentListItem(
            doc_id=d.doc_id,
            file_name=d.file_name,
            status=d.status,
            engine=d.engine,
            page_count=d.page_count,
            created_at=d.created_at.isoformat() if d.created_at else "",
        )
        for d in docs
    ]


@router.delete("/{doc_id}", response_model=DeleteResponse)
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeleteResponse:
    doc = await db.get(Document, doc_id)
    if not doc or doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        success = await file_service_client.delete_document(doc_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in file-service")
        return DeleteResponse(deleted=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Delete document failed")
        raise HTTPException(status_code=500, detail=str(e))
