"""
Async gRPC servicer — implements FileService RPC methods.
Orchestrates: MinIO upload → PaddleOCR → PageIndex → PostgreSQL.
All I/O is async; CPU-bound OCR runs via asyncio.to_thread.
"""

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
from app.services.minio import minio_service
from app.services.paddleocr import process_file_async
from app.services.pageindex import build_tree, save_to_db

# Generated protobuf — will be created from .proto file
from app.proto import file_service_pb2, file_service_pb2_grpc

logger = logging.getLogger(__name__)

# In-memory status tracker
_doc_status: Dict[str, dict] = {}


def _content_type_from_ext(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "tiff": "image/tiff",
        "tif": "image/tiff",
        "bmp": "image/bmp",
    }.get(ext, "application/octet-stream")


class FileServiceServicer(file_service_pb2_grpc.FileServiceServicer):
    """Async gRPC servicer for document processing pipeline."""

    async def ProcessDocument(self, request, context):
        doc_id = str(uuid.uuid4())
        file_name = request.file_name
        file_data = request.file_data
        user_id = request.user_id

        logger.info("ProcessDocument: doc_id=%s file=%s user=%s size=%d",
                     doc_id, file_name, user_id, len(file_data))

        _doc_status[doc_id] = {"status": "processing", "file_name": file_name,
                                "message": "Uploading to MinIO..."}

        try:
            # Step 1: Upload to MinIO (async)
            ext = file_name.rsplit(".", 1)[-1] if "." in file_name else "bin"
            minio_key = f"{doc_id}.{ext}"
            content_type = _content_type_from_ext(file_name)
            await minio_service.upload_bytes(minio_key, file_data, content_type)
            logger.info("[%s] 1/4 Uploaded to MinIO: %s", doc_id, minio_key)

            _doc_status[doc_id]["message"] = "Running OCR (PP-StructureV3)..."

            # Step 2: Write temp file + OCR (CPU-bound, runs in thread)
            os.makedirs(settings.temp_dir, exist_ok=True)
            temp_path = os.path.join(settings.temp_dir, f"{doc_id}.{ext}")
            await asyncio.to_thread(_write_bytes, temp_path, file_data)

            markdown_text, md_path, bbox_index = await process_file_async(temp_path, minio_key)
            logger.info("[%s] 2/4 OCR done, %d chars", doc_id, len(markdown_text))

            _doc_status[doc_id]["message"] = "Building PageIndex tree..."

            # Step 3: Build PageIndex tree (LLM calls, async)
            tree = await build_tree(md_path)
            logger.info("[%s] 3/4 PageIndex tree built", doc_id)

            _doc_status[doc_id]["message"] = "Saving to database..."

            # Step 4: Save to PostgreSQL (async)
            async with get_db_context() as db:
                node_count = await save_to_db(
                    db, doc_id, file_name, minio_key, user_id, tree, markdown_text,
                )
            logger.info("[%s] 4/4 Saved to DB, %d nodes", doc_id, node_count)

            # Cleanup temp files
            for p in [temp_path, md_path]:
                if p and os.path.exists(p):
                    os.remove(p)

            _doc_status[doc_id] = {
                "status": "completed", "file_name": file_name,
                "node_count": node_count,
                "message": f"Processed: {node_count} nodes indexed",
            }

            return file_service_pb2.ProcessDocumentResponse(
                doc_id=doc_id, minio_key=minio_key,
                status="completed",
                message=f"Processed: {node_count} nodes indexed",
            )

        except Exception as e:
            logger.error("[%s] Failed: %s\n%s", doc_id, e, traceback.format_exc())
            _doc_status[doc_id] = {
                "status": "failed", "file_name": file_name, "message": str(e),
            }
            return file_service_pb2.ProcessDocumentResponse(
                doc_id=doc_id, minio_key="", status="failed",
                message=f"Failed: {e}",
            )

    async def GetDocumentStatus(self, request, context):
        doc_id = request.doc_id
        info = _doc_status.get(doc_id)

        if info:
            return file_service_pb2.GetDocumentStatusResponse(
                doc_id=doc_id, status=info["status"],
                file_name=info.get("file_name", ""),
                node_count=info.get("node_count", 0),
                message=info.get("message", ""),
            )

        # Fallback: check DB via ORM
        async with get_db_context() as db:
            doc = await db.get(Document, doc_id)
            if doc:
                count_result = await db.execute(
                    select(func.count(DocumentNode.node_id))
                    .where(DocumentNode.doc_id == doc_id)
                )
                cnt = count_result.scalar() or 0
                return file_service_pb2.GetDocumentStatusResponse(
                    doc_id=doc_id, status=doc.status or "completed",
                    file_name=doc.file_name, node_count=cnt,
                    message="Document indexed",
                )

        await context.abort(grpc.StatusCode.NOT_FOUND, f"Document {doc_id} not found")

    async def DeleteDocument(self, request, context):
        doc_id = request.doc_id

        async with get_db_context() as db:
            doc = await db.get(Document, doc_id)
            if not doc:
                return file_service_pb2.DeleteDocumentResponse(
                    success=False, message=f"Document {doc_id} not found",
                )

            # Delete from MinIO
            try:
                await minio_service.delete_object(doc.minio_key)
            except Exception as e:
                logger.warning("MinIO delete failed: %s", e)

            # Delete from DB (cascade via relationship)
            await db.delete(doc)

        _doc_status.pop(doc_id, None)
        return file_service_pb2.DeleteDocumentResponse(
            success=True, message=f"Document {doc_id} deleted",
        )


def _write_bytes(path: str, data: bytes):
    with open(path, "wb") as f:
        f.write(data)


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
