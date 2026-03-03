"""
Async gRPC client for file-service.

Provides a thin async wrapper around the generated protobuf stubs.
Used by backend agent nodes (document_tools.py) and REST API routes.

Note: The proto stubs (file_service_pb2 / file_service_pb2_grpc) must be
generated before import. Add to your Makefile / startup:
  python -m grpc_tools.protoc -I. \
      --python_out=. --grpc_python_out=. \
      file_service/app/proto/file_service.proto
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

import grpc
from grpc import aio as grpc_aio

from core.config import settings

logger = logging.getLogger(__name__)

_channel: Optional[grpc_aio.Channel] = None
_stub = None

# ── Response dataclasses ───────────────────────────────────────────────

@dataclass
class CitationItem:
    node_id: str
    node_title: str
    layout_type: str   # "text"|"table"|"figure"|"formula"
    page: int
    bbox: List[float]
    section_url: str   # MinIO presigned URL
    content_preview: str


@dataclass
class RetrievalResult:
    answer: str
    citations: List[CitationItem]
    doc_id: str


@dataclass
class KnowledgeChunk:
    text: str
    score: float
    doc_id: str
    node_id: str
    node_title: str
    page: int
    layout_type: str
    section_url: str


@dataclass
class DocumentInfo:
    doc_id: str
    file_name: str
    status: str
    engine: str
    page_count: int
    created_at: str


def _get_stub():
    """Lazy-init gRPC channel + stub to file-service."""
    global _channel, _stub
    if _stub is not None:
        return _stub

    # Import generated stubs — must be on sys.path
    try:
        import sys, os
        # file-service proto dir relative to backend
        proto_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "file-service", "app"
        )
        if proto_path not in sys.path:
            sys.path.insert(0, proto_path)
        from proto import file_service_pb2, file_service_pb2_grpc
    except ImportError as e:
        raise ImportError(
            "file_service protobuf stubs not found. Run grpc_tools.protoc to generate them."
        ) from e

    _channel = grpc_aio.insecure_channel(settings.file_service_grpc_url)
    _stub = file_service_pb2_grpc.FileServiceStub(_channel)
    return _stub




# ── gRPC client ────────────────────────────────────────────────────────

class FileServiceClient:
    """Async gRPC client for file-service."""

    async def process_document(
        self,
        file_name: str,
        file_data: bytes,
        user_id: str,
    ) -> dict:
        """Upload + extract + index a document. Returns {doc_id, minio_key, engine, page_count}."""
        from proto import file_service_pb2
        stub = _get_stub()
        resp = await stub.ProcessDocument(file_service_pb2.ProcessDocumentRequest(
            file_name=file_name,
            file_data=file_data,
            user_id=user_id,
        ))
        return {
            "doc_id": resp.doc_id,
            "minio_key": resp.minio_key,
            "status": resp.status,
            "message": resp.message,
            "engine": resp.engine,
            "page_count": resp.page_count,
        }

    async def get_document_status(self, doc_id: str) -> dict:
        from proto import file_service_pb2
        stub = _get_stub()
        resp = await stub.GetDocumentStatus(
            file_service_pb2.GetDocumentStatusRequest(doc_id=doc_id)
        )
        return {
            "doc_id": resp.doc_id,
            "status": resp.status,
            "file_name": resp.file_name,
            "node_count": resp.node_count,
            "message": resp.message,
            "engine": resp.engine,
        }

    async def retrieve(self, doc_id: str, question: str) -> RetrievalResult:
        """PageIndex reasoning retrieval for a specific document."""
        from proto import file_service_pb2
        stub = _get_stub()
        resp = await stub.RetrieveDocument(file_service_pb2.RetrieveDocumentRequest(
            doc_id=doc_id,
            question=question,
        ))
        citations = [
            CitationItem(
                node_id=c.node_id,
                node_title=c.node_title,
                layout_type=c.layout_type,
                page=c.page,
                bbox=list(c.bbox),
                section_url=c.section_url,
                content_preview=c.content_preview,
            )
            for c in resp.citations
        ]
        return RetrievalResult(answer=resp.answer, citations=citations, doc_id=resp.doc_id)

    async def knowledge_search(
        self,
        user_id: str,
        query: str,
        top_k: int = 8,
        filter_doc_ids: Optional[List[str]] = None,
    ) -> List[KnowledgeChunk]:
        """Milvus semantic search across user's knowledge base."""
        from proto import file_service_pb2
        stub = _get_stub()
        resp = await stub.KnowledgeSearch(file_service_pb2.KnowledgeSearchRequest(
            user_id=user_id,
            query=query,
            top_k=top_k,
            doc_ids=filter_doc_ids or [],
        ))
        return [
            KnowledgeChunk(
                text=c.text,
                score=c.score,
                doc_id=c.doc_id,
                node_id=c.node_id,
                node_title=c.node_title,
                page=c.page,
                layout_type=c.layout_type,
                section_url=c.section_url,
            )
            for c in resp.chunks
        ]

    async def list_documents(self, user_id: str) -> List[DocumentInfo]:
        from proto import file_service_pb2
        stub = _get_stub()
        resp = await stub.ListDocuments(
            file_service_pb2.ListDocumentsRequest(user_id=user_id)
        )
        return [
            DocumentInfo(
                doc_id=d.doc_id,
                file_name=d.file_name,
                status=d.status,
                engine=d.engine,
                page_count=d.page_count,
                created_at=d.created_at,
            )
            for d in resp.documents
        ]

    async def delete_document(self, doc_id: str) -> bool:
        from proto import file_service_pb2
        stub = _get_stub()
        resp = await stub.DeleteDocument(
            file_service_pb2.DeleteDocumentRequest(doc_id=doc_id)
        )
        return resp.success


# Module-level singleton
file_service_client = FileServiceClient()
