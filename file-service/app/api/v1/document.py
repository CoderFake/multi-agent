"""
Document API routes — FastAPI endpoints for document management + retrieval.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.document import Document, DocumentNode, DocumentTree
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    RetrievalResponse,
)
from app.services.retrieval import retrieve

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    user_id: str = Query(..., description="Firebase UID"),
    db: AsyncSession = Depends(get_db),
):
    """List all documents for a user."""
    # Documents with node count
    stmt = (
        select(
            Document,
            func.count(DocumentNode.node_id).label("node_count"),
        )
        .outerjoin(DocumentNode, Document.doc_id == DocumentNode.doc_id)
        .where(Document.user_id == user_id)
        .group_by(Document.doc_id)
        .order_by(Document.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    documents = [
        DocumentResponse(
            doc_id=doc.doc_id,
            file_name=doc.file_name,
            minio_key=doc.minio_key,
            status=doc.status,
            node_count=cnt,
            created_at=doc.created_at,
        )
        for doc, cnt in rows
    ]

    return DocumentListResponse(documents=documents, total=len(documents))


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Get document details with node count."""
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    count_result = await db.execute(
        select(func.count(DocumentNode.node_id))
        .where(DocumentNode.doc_id == doc_id)
    )
    cnt = count_result.scalar() or 0

    return DocumentResponse(
        doc_id=doc.doc_id,
        file_name=doc.file_name,
        minio_key=doc.minio_key,
        status=doc.status,
        node_count=cnt,
        created_at=doc.created_at,
    )


@router.get("/{doc_id}/tree")
async def get_document_tree(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Get the PageIndex tree JSON for a document."""
    tree = await db.get(DocumentTree, doc_id)
    if not tree:
        raise HTTPException(status_code=404, detail="Document tree not found")

    return {"doc_id": doc_id, "tree_json": tree.tree_json}


@router.post("/{doc_id}/query", response_model=RetrievalResponse)
async def query_document(
    doc_id: str,
    query: str = Query(..., description="User query"),
    db: AsyncSession = Depends(get_db),
):
    """
    Reasoning-based retrieval using PageIndex tree search.
    LLM selects relevant nodes → fetches content → generates answer with citations.
    """
    try:
        return await retrieve(db, doc_id, query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a document and all its nodes/trees (cascade)."""
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from MinIO
    from app.services.minio import minio_service
    try:
        await minio_service.delete_object(doc.minio_key)
    except Exception as e:
        logger.warning("MinIO delete failed for %s: %s", doc.minio_key, e)

    await db.delete(doc)
    return {"success": True, "message": f"Document {doc_id} deleted"}
