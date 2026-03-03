"""
Async gRPC servicer — implements FileService RPC methods.

Pipeline (ProcessDocument):
  1. Upload to MinIO
  2. Write temp file + Hybrid Extract (Docling / PP-StructureV3)
  3. Build PageIndex tree (LLM)
  4. Save to PostgreSQL (document.save_document)
  5. Upsert chunks into Milvus knowledge base
  6. Cleanup temp files

Additional RPCs:
  - RetrieveDocument: PageIndex reasoning retrieval for a specific doc
  - KnowledgeSearch:  Milvus semantic search across user's knowledge base
  - ListDocuments:    List all user documents
  - GetDocumentStatus / DeleteDocument: management
"""

from __future__ import annotations

import asyncio
import logging
import os
import traceback
import uuid
from typing import Dict

import grpc
from grpc import aio as grpc_aio
from sqlalchemy import select, func

from app.config.settings import settings
from app.core.database import get_db_context
from app.models.document import Document, DocumentNode
from app.services.document import save_document, get_document, list_by_user, delete_document
from app.services.extract import get_extractor, build_tree, flatten_nodes
from app.services.milvus import milvus_service, nodes_to_chunks
from app.services.minio import minio_service
from app.services.retrieval import retrieve

# Generated protobuf stubs
from app.proto import file_service_pb2, file_service_pb2_grpc

logger = logging.getLogger(__name__)

# In-memory status tracker (hot-path; real status always in DB)
_doc_status: Dict[str, dict] = {}


def _content_type_from_ext(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "html": "text/html",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "tiff": "image/tiff",
        "tif": "image/tiff",
        "bmp": "image/bmp",
    }.get(ext, "application/octet-stream")


def _write_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


class FileServiceServicer(file_service_pb2_grpc.FileServiceServicer):
    """Async gRPC servicer for document processing pipeline."""

    # ─────────────────────────────────────────────────────────────────────
    # ProcessDocument
    # ─────────────────────────────────────────────────────────────────────
    async def ProcessDocument(self, request, context):
        doc_id = str(uuid.uuid4())
        file_name = request.file_name
        file_data = request.file_data
        user_id = request.user_id

        logger.info("ProcessDocument: doc_id=%s file=%s user=%s size=%d",
                    doc_id, file_name, user_id, len(file_data))

        _doc_status[doc_id] = {
            "status": "processing", "file_name": file_name,
            "message": "Uploading to MinIO…",
        }
        temp_path = ""
        md_path = ""

        try:
            # ── 1. Upload original file to MinIO ──────────────────────
            ext = file_name.rsplit(".", 1)[-1] if "." in file_name else "bin"
            minio_key = f"{doc_id}.{ext}"
            content_type = _content_type_from_ext(file_name)
            await minio_service.upload_bytes(minio_key, file_data, content_type)
            logger.info("[%s] 1/5 Uploaded original to MinIO: %s", doc_id, minio_key)

            # ── 2. Write temp file + Hybrid Extract ───────────────────
            _doc_status[doc_id]["message"] = "Extracting document (Hybrid)…"
            os.makedirs(settings.temp_dir, exist_ok=True)
            temp_path = os.path.join(settings.temp_dir, f"{doc_id}.{ext}")
            await asyncio.to_thread(_write_bytes, temp_path, file_data)

            extractor = get_extractor()
            result = await extractor.extract(temp_path, minio_key)
            md_path = result.md_path
            logger.info("[%s] 2/5 Extract done (engine=%s), %d blocks, %d pages",
                        doc_id, result.engine, len(result.blocks), result.page_count)

            # ── 3. Build PageIndex tree ───────────────────────────────
            _doc_status[doc_id]["message"] = "Building reasoning tree (PageIndex)…"
            tree = await build_tree(result.md_path)
            logger.info("[%s] 3/5 PageIndex tree built", doc_id)

            # ── 4. Save to PostgreSQL + upload section images ─────────
            _doc_status[doc_id]["message"] = "Saving to database…"
            async with get_db_context() as db:
                node_count = await save_document(
                    db=db,
                    file_path=temp_path,
                    doc_id=doc_id,
                    file_name=file_name,
                    minio_key=minio_key,
                    user_id=user_id,
                    tree=tree,
                    result=result,
                )
            logger.info("[%s] 4/5 Saved to DB: %d nodes", doc_id, node_count)

            # ── 5. Upsert chunks into Milvus ──────────────────────────
            _doc_status[doc_id]["message"] = "Indexing knowledge base (Milvus)…"
            flat_nodes = flatten_nodes(tree)
            # Build bbox map from flat_nodes content for section_url lookup
            bbox_map: dict = {}
            md_lines = result.markdown.split("\n")
            from app.services.extract.pageindex import extract_bbox_from_content
            for node in flat_nodes:
                start, end = node["start_index"], node["end_index"]
                content = "\n".join(md_lines[start:end + 1]) if end < len(md_lines) else "\n".join(md_lines[start:])
                _, bboxes = extract_bbox_from_content(content)
                # Annotate with minio_key from result.blocks
                for bbox_item in bboxes:
                    matching = next(
                        (b for b in result.blocks
                         if b.page == bbox_item["page"] and b.bbox == bbox_item["bbox"] and b.minio_key),
                        None,
                    )
                    if matching:
                        bbox_item["minio_key"] = matching.minio_key
                bbox_map[node["node_id"]] = bboxes

            chunks = nodes_to_chunks(flat_nodes, doc_id, user_id, bbox_map)
            await milvus_service.upsert_chunks(chunks)
            logger.info("[%s] 5/5 Milvus upsert: %d chunks", doc_id, len(chunks))

            # ── Cleanup temp files ────────────────────────────────────
            for p in [temp_path, md_path]:
                if p and os.path.exists(p):
                    os.remove(p)

            _doc_status[doc_id] = {
                "status": "completed", "file_name": file_name,
                "node_count": node_count, "engine": result.engine,
                "message": f"Processed: {node_count} nodes indexed",
            }

            return file_service_pb2.ProcessDocumentResponse(
                doc_id=doc_id, minio_key=minio_key,
                status="completed",
                message=f"Processed: {node_count} nodes indexed",
                engine=result.engine,
                page_count=result.page_count,
            )

        except Exception as e:
            logger.error("[%s] Failed: %s\n%s", doc_id, e, traceback.format_exc())
            _doc_status[doc_id] = {
                "status": "failed", "file_name": file_name, "message": str(e),
            }
            for p in [temp_path, md_path]:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            return file_service_pb2.ProcessDocumentResponse(
                doc_id=doc_id, minio_key="", status="failed",
                message=f"Failed: {e}",
            )

    # ─────────────────────────────────────────────────────────────────────
    # GetDocumentStatus
    # ─────────────────────────────────────────────────────────────────────
    async def GetDocumentStatus(self, request, context):
        doc_id = request.doc_id
        info = _doc_status.get(doc_id)

        if info:
            return file_service_pb2.GetDocumentStatusResponse(
                doc_id=doc_id,
                status=info["status"],
                file_name=info.get("file_name", ""),
                node_count=info.get("node_count", 0),
                message=info.get("message", ""),
                engine=info.get("engine", ""),
            )

        # Fallback: query DB
        async with get_db_context() as db:
            doc = await db.get(Document, doc_id)
            if doc:
                cnt_result = await db.execute(
                    select(func.count(DocumentNode.node_id))
                    .where(DocumentNode.doc_id == doc_id)
                )
                cnt = cnt_result.scalar() or 0
                return file_service_pb2.GetDocumentStatusResponse(
                    doc_id=doc_id,
                    status=doc.status or "completed",
                    file_name=doc.file_name,
                    node_count=cnt,
                    message="Document indexed",
                    engine=doc.engine or "",
                )

        await context.abort(grpc.StatusCode.NOT_FOUND, f"Document {doc_id} not found")

    # ─────────────────────────────────────────────────────────────────────
    # DeleteDocument
    # ─────────────────────────────────────────────────────────────────────
    async def DeleteDocument(self, request, context):
        doc_id = request.doc_id
        async with get_db_context() as db:
            doc = await db.get(Document, doc_id)
            if not doc:
                return file_service_pb2.DeleteDocumentResponse(
                    success=False, message=f"Document {doc_id} not found",
                )
            try:
                await minio_service.delete_object(doc.minio_key)
            except Exception as e:
                logger.warning("MinIO delete failed for %s: %s", doc.minio_key, e)

            await delete_document(db, doc_id)

        # Remove Milvus chunks
        await milvus_service.delete_by_doc(doc_id)
        _doc_status.pop(doc_id, None)

        return file_service_pb2.DeleteDocumentResponse(
            success=True, message=f"Document {doc_id} deleted",
        )

    # ─────────────────────────────────────────────────────────────────────
    # RetrieveDocument — PageIndex reasoning retrieval
    # ─────────────────────────────────────────────────────────────────────
    async def RetrieveDocument(self, request, context):
        doc_id = request.doc_id
        question = request.question

        async with get_db_context() as db:
            try:
                response = await retrieve(db, doc_id, question)
            except ValueError as e:
                await context.abort(grpc.StatusCode.NOT_FOUND, str(e))
                return

        # Generate presigned URLs for section_url citations
        citations_pb = []
        for cit in response.citations:
            # Fetch presigned URLs for each bbox's minio_key
            section_url = ""
            if cit.bboxes:
                raw_key = cit.bboxes[0].bbox if hasattr(cit.bboxes[0], "bbox") else None
                # section_url already populated by retrieval.py via presigned_url
                section_url = cit.source_url or ""

            citations_pb.append(file_service_pb2.CitationItem(
                node_id=cit.node_id,
                node_title=cit.title,
                layout_type="text",
                page=cit.pages[0] if cit.pages else 0,
                bbox=[float(v) for v in (cit.bboxes[0].bbox if cit.bboxes else [])],
                section_url=section_url,
                content_preview="",
            ))

        return file_service_pb2.RetrieveDocumentResponse(
            answer=response.answer,
            citations=citations_pb,
            doc_id=doc_id,
        )

    # ─────────────────────────────────────────────────────────────────────
    # KnowledgeSearch — Milvus RAG search
    # ─────────────────────────────────────────────────────────────────────
    async def KnowledgeSearch(self, request, context):
        user_id = request.user_id
        query = request.query
        top_k = request.top_k or 8
        filter_doc_ids = list(request.doc_ids) if request.doc_ids else []

        chunks = await milvus_service.search(
            query=query,
            user_id=user_id,
            top_k=top_k,
            filter_doc_ids=filter_doc_ids,
        )

        # Generate presigned URLs for MinIO section keys
        chunk_pbs = []
        for chunk in chunks:
            section_url = chunk.section_url
            if section_url and not section_url.startswith("http"):
                try:
                    section_url = await minio_service.get_presigned_url(section_url)
                except Exception:
                    section_url = ""

            chunk_pbs.append(file_service_pb2.KnowledgeChunk(
                text=chunk.text,
                score=chunk.score,
                doc_id=chunk.doc_id,
                node_id=chunk.node_id,
                node_title=chunk.node_title,
                page=chunk.page,
                layout_type=chunk.layout_type,
                section_url=section_url,
            ))

        return file_service_pb2.KnowledgeSearchResponse(chunks=chunk_pbs)

    # ─────────────────────────────────────────────────────────────────────
    # ListDocuments
    # ─────────────────────────────────────────────────────────────────────
    async def ListDocuments(self, request, context):
        async with get_db_context() as db:
            docs = await list_by_user(db, request.user_id)

        doc_pbs = [
            file_service_pb2.DocumentInfo(
                doc_id=doc.doc_id,
                file_name=doc.file_name,
                status=doc.status or "",
                engine=doc.engine or "",
                page_count=doc.page_count or 0,
                created_at=doc.created_at.isoformat() if doc.created_at else "",
            )
            for doc in docs
        ]
        return file_service_pb2.ListDocumentsResponse(documents=doc_pbs)


# ── gRPC server startup ────────────────────────────────────────────────

async def start_grpc_server() -> grpc_aio.Server:
    """Start async gRPC server."""
    server = grpc_aio.server(
        options=[
            ("grpc.max_receive_message_length", 100 * 1024 * 1024),
            ("grpc.max_send_message_length", 100 * 1024 * 1024),
        ],
    )
    file_service_pb2_grpc.add_FileServiceServicer_to_server(
        FileServiceServicer(), server,
    )
    listen_addr = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(listen_addr)
    await server.start()
    logger.info("Async gRPC FileService on %s", listen_addr)
    return server
