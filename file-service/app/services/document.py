"""
Document service — all database + MinIO operations for document processing.
This is the ONLY place that touches SQLAlchemy or MinIO within the document pipeline.

Called by grpc.py after extraction + tree building.
"""

from __future__ import annotations

import hashlib
import io
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentNode, DocumentTree
from app.services.extract.base import BlockMeta, ExtractResult, VISUAL_BLOCK_TYPES
from app.services.extract.pageindex import flatten_nodes, extract_bbox_from_content
from app.services.minio import minio_service

logger = logging.getLogger(__name__)


# ── Section image upload ───────────────────────────────────────────────

async def _upload_section(
    doc_id: str,
    file_path: str,
    block: BlockMeta,
    block_idx: int,
) -> str:
    """
    Crop and upload a visual block (table/figure/formula) to MinIO.
    Returns the MinIO object key for the section.
    """
    try:
        from PIL import Image

        img = Image.open(file_path)
        if img.mode == "RGBA":
            img = img.convert("RGB")

        x0, y0, x1, y1 = [int(v) for v in block.bbox[:4]]
        section = img.crop((x0, y0, x1, y1))

        buf = io.BytesIO()
        section.save(buf, format="PNG")
        buf.seek(0)
        data = buf.read()

    except Exception as e:
        logger.debug("Section crop failed (non-image doc): %s", e)
        data = b""  # Skip upload for non-image pages (e.g. native PDF)

    if not data:
        return ""

    bbox_hash = hashlib.md5(str(block.bbox).encode()).hexdigest()[:8]
    key = f"sections/{doc_id}/{block.page}_{block.layout_type}_{block_idx}_{bbox_hash}.png"
    await minio_service.upload_bytes(key, data, "image/png")
    return key


# ── Main entry point ───────────────────────────────────────────────────

async def save_document(
    db: AsyncSession,
    file_path: str,           # local temp path (for section image cropping)
    doc_id: str,
    file_name: str,
    minio_key: str,
    user_id: str,
    tree: Dict[str, Any],
    result: ExtractResult,
    bucket: str = "documents",
) -> int:
    """
    Persist a processed document to PostgreSQL and upload section images to MinIO.

    Steps:
      1. Upload visual section crops (tables/figures/formulas) → MinIO
      2. Annotate blocks with their MinIO keys
      3. Upsert Document, DocumentTree, DocumentNodes
      4. Return node count
    """

    # ── 1. Upload visual sections to MinIO ────────────────────────────
    for idx, block in enumerate(result.blocks):
        if block.layout_type in VISUAL_BLOCK_TYPES and block.bbox:
            section_key = await _upload_section(doc_id, file_path, block, idx)
            block.minio_key = section_key

    # ── 2. Upsert Document ────────────────────────────────────────────
    doc = await db.get(Document, doc_id)
    if doc:
        doc.file_name = file_name
        doc.minio_key = minio_key
        doc.user_id = user_id
        doc.status = "completed"
        doc.engine = result.engine
        doc.page_count = result.page_count
    else:
        doc = Document(
            doc_id=doc_id,
            file_name=file_name,
            minio_key=minio_key,
            bucket=bucket,
            user_id=user_id,
            status="completed",
            engine=result.engine,
            page_count=result.page_count,
        )
        db.add(doc)

    # ── 3. Upsert DocumentTree ────────────────────────────────────────
    tree_obj = await db.get(DocumentTree, doc_id)
    if tree_obj:
        tree_obj.tree_json = tree
    else:
        tree_obj = DocumentTree(doc_id=doc_id, tree_json=tree)
        db.add(tree_obj)

    await db.flush()

    # ── 4. Upsert DocumentNodes ───────────────────────────────────────
    flat_nodes = flatten_nodes(tree)
    md_lines = result.markdown.split("\n")

    for node in flat_nodes:
        start = node["start_index"]
        end = node["end_index"]
        content = (
            "\n".join(md_lines[start:end + 1])
            if end < len(md_lines)
            else "\n".join(md_lines[start:])
        )

        page_list, bbox_list = extract_bbox_from_content(content)

        # Annotate bbox_list with minio_key from block metadata
        for bbox_item in bbox_list:
            matching = next(
                (b for b in result.blocks
                 if b.page == bbox_item["page"]
                 and b.bbox == bbox_item["bbox"]
                 and b.minio_key),
                None,
            )
            if matching:
                bbox_item["minio_key"] = matching.minio_key

        existing = await db.get(DocumentNode, (node["node_id"], doc_id))
        if existing:
            existing.parent_id = node.get("parent_id")
            existing.title = node["title"]
            existing.summary = node.get("summary", "")
            existing.content = content
            existing.start_index = start
            existing.end_index = end
            existing.pages = page_list
            existing.bboxes = bbox_list
        else:
            db.add(DocumentNode(
                node_id=node["node_id"],
                doc_id=doc_id,
                parent_id=node.get("parent_id"),
                title=node["title"],
                summary=node.get("summary", ""),
                content=content,
                start_index=start,
                end_index=end,
                pages=page_list,
                bboxes=bbox_list,
            ))

    await db.flush()
    logger.info("Saved doc_id=%s, engine=%s, %d nodes", doc_id, result.engine, len(flat_nodes))
    return len(flat_nodes)


# ── Retrieval helpers ──────────────────────────────────────────────────

async def get_document(db: AsyncSession, doc_id: str) -> Optional[Document]:
    return await db.get(Document, doc_id)


async def list_by_user(db: AsyncSession, user_id: str) -> List[Document]:
    from sqlalchemy import select
    result = await db.execute(
        select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_document(db: AsyncSession, doc_id: str) -> bool:
    """Delete Document from DB (cascade removes tree + nodes). MinIO cleanup done in grpc.py."""
    doc = await db.get(Document, doc_id)
    if not doc:
        return False
    await db.delete(doc)
    return True
