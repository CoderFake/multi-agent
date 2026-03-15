"""Index service — full file-based indexing pipeline with progress tracking.

Pipeline:
  1. Lock check (dedup)
  2. Download file from MinIO
  3. Extract (HybridExtractor)
  4. Chunk (overlapping text chunks)
  5. Embed (sentence-transformers)
  6. Insert into Milvus with access control
  7. Update progress → Redis
"""

from __future__ import annotations

import hashlib
import logging
import os
import traceback
from typing import List

from app.config.settings import settings
from app.core.milvus import (
    delete_document_chunks,
    get_collection_name,
    insert_chunks,
)
from app.core.minio_client import download_file
from app.core.redis import (
    acquire_lock,
    release_lock,
    update_task_progress,
)
from app.schemas.events import IndexTaskPayload, TaskStatus
from app.services.extract.chunker import TextChunk, chunk_text
from app.services.extract.hybrid import get_extractor
from app.utils.embeddings import embed_texts

logger = logging.getLogger(__name__)


def _file_hash(storage_path: str) -> str:
    """Generate hash from storage path for dedup lock."""
    return hashlib.md5(storage_path.encode()).hexdigest()


async def process_indexing_task(payload: IndexTaskPayload) -> None:
    """
    Full indexing pipeline. Pushes progress to Redis at each step.
    """
    job_id = payload.job_id
    doc_id = payload.document_id
    org_id = payload.org_id
    file_hash = _file_hash(payload.storage_path)

    collection_name = get_collection_name(payload.org_subdomain, payload.agent_code)

    try:
        # ── 1. Lock check ─────────────────────────────────────────────
        if not acquire_lock(org_id, file_hash):
            update_task_progress(
                job_id=job_id,
                status=TaskStatus.FAILED,
                progress=0,
                message="Duplicate file is already being processed",
                document_id=doc_id,
            )
            logger.warning("Duplicate lock: %s/%s", org_id, file_hash)
            return

        update_task_progress(
            job_id=job_id,
            status=TaskStatus.EXTRACTING,
            progress=5,
            message="Downloading file from storage...",
            document_id=doc_id,
        )

        # ── 2. Download file ──────────────────────────────────────────
        local_path = download_file(payload.storage_path)

        update_task_progress(
            job_id=job_id,
            status=TaskStatus.EXTRACTING,
            progress=10,
            message="Extracting document content...",
            document_id=doc_id,
        )

        # ── 3. Extract ────────────────────────────────────────────────
        extractor = get_extractor()
        extract_result = await extractor.extract(local_path, payload.storage_path)

        update_task_progress(
            job_id=job_id,
            status=TaskStatus.CHUNKING,
            progress=30,
            message=f"Extracted {len(extract_result.blocks)} blocks ({extract_result.engine}). Chunking...",
            document_id=doc_id,
        )

        # ── 4. Chunk ─────────────────────────────────────────────────
        full_text = extract_result.markdown or ""
        if not full_text.strip():
            # Fallback: concatenate block texts
            full_text = "\n\n".join(b.text for b in extract_result.blocks if b.text)

        chunks: List[TextChunk] = chunk_text(full_text)
        total_chunks = len(chunks)

        if total_chunks == 0:
            update_task_progress(
                job_id=job_id,
                status=TaskStatus.COMPLETED,
                progress=100,
                message="No text content found in document",
                total_chunks=0,
                document_id=doc_id,
            )
            return

        update_task_progress(
            job_id=job_id,
            status=TaskStatus.EMBEDDING,
            progress=50,
            message=f"Embedding {total_chunks} chunks...",
            total_chunks=total_chunks,
            document_id=doc_id,
        )

        # ── 5. Embed ─────────────────────────────────────────────────
        chunk_texts = [c.text for c in chunks]
        embeddings = embed_texts(chunk_texts)

        update_task_progress(
            job_id=job_id,
            status=TaskStatus.INDEXING,
            progress=80,
            message="Inserting into vector database...",
            total_chunks=total_chunks,
            processed_chunks=total_chunks,
            document_id=doc_id,
        )

        # ── 6. Delete old chunks and insert new ──────────────────────
        try:
            delete_document_chunks(collection_name, doc_id)
        except Exception:
            pass  # Collection may not exist yet

        group_ids_str = ",".join(payload.group_ids)

        insert_chunks(
            collection_name=collection_name,
            chunk_ids=[f"{doc_id}_{c.chunk_index}" for c in chunks],
            document_ids=[doc_id] * total_chunks,
            folder_ids=[payload.folder_id] * total_chunks,
            org_ids=[org_id] * total_chunks,
            access_types=[payload.access_type] * total_chunks,
            group_ids_list=[group_ids_str] * total_chunks,
            file_names=[payload.file_name] * total_chunks,
            texts=[c.text[:65534] for c in chunks],
            chunk_indices=[c.chunk_index for c in chunks],
            pages=[0] * total_chunks,  # TODO: map chunks to pages from blocks
            layout_types=["text"] * total_chunks,
            section_urls=[""] * total_chunks,
            embeddings=embeddings,
        )

        # ── 7. Done ──────────────────────────────────────────────────
        update_task_progress(
            job_id=job_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message=f"Indexed {total_chunks} chunks successfully",
            total_chunks=total_chunks,
            processed_chunks=total_chunks,
            document_id=doc_id,
        )
        logger.info(
            "Indexing completed: job=%s doc=%s chunks=%d collection=%s",
            job_id, doc_id, total_chunks, collection_name,
        )

    except Exception as e:
        logger.error("Indexing failed: job=%s error=%s", job_id, e)
        logger.error(traceback.format_exc())
        update_task_progress(
            job_id=job_id,
            status=TaskStatus.FAILED,
            progress=0,
            message="Indexing failed",
            error=str(e),
            document_id=doc_id,
        )

    finally:
        # Always release lock
        release_lock(org_id, file_hash)

        # Cleanup temp files
        try:
            local_path_var = os.path.join(settings.TEMP_DIR, os.path.basename(payload.storage_path))
            if os.path.exists(local_path_var):
                os.remove(local_path_var)
        except Exception:
            pass


class IndexService:
    """Backward-compatible indexing service for routes/index.py (direct API)."""

    async def index_documents(self, request) -> dict:
        """Embed and insert pre-chunked documents (old API).

        Uses asyncio.to_thread() because pymilvus + embedding are synchronous.
        """
        import asyncio
        from app.schemas.index import IndexResponse
        from app.utils.embeddings import embed_batch

        collection_name = request.collection_name
        texts = [doc.text for doc in request.documents]
        embeddings = await asyncio.to_thread(embed_batch, texts)

        n = len(request.documents)
        chunk_ids = [doc.id for doc in request.documents]
        document_ids = [request.team_id] * n
        folder_ids = [""] * n
        org_ids = [request.team_id] * n
        access_types = ["public"] * n
        group_ids_list = [""] * n
        file_names = [doc.file_name for doc in request.documents]
        chunk_indices = [doc.chunk_index for doc in request.documents]
        pages = [0] * n
        layout_types = ["text"] * n
        section_urls = [doc.source for doc in request.documents]

        await asyncio.to_thread(
            insert_chunks,
            collection_name,
            chunk_ids, document_ids, folder_ids, org_ids,
            access_types, group_ids_list, file_names,
            texts, chunk_indices, pages, layout_types,
            section_urls, embeddings,
        )

        return IndexResponse(
            indexed=n,
            collection_name=collection_name,
        )


# Module-level singleton
index_svc = IndexService()

