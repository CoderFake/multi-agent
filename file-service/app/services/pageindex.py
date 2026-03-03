"""
Async PageIndex service — build hierarchical tree index from Markdown.

Uses the pageindex library to create a reasoning-friendly tree structure.
Each node gets title, summary, start/end indices into the markdown.
DB operations use async SQLAlchemy; CPU/LLM work runs via asyncio.to_thread.
"""

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.document import Document, DocumentNode, DocumentTree

logger = logging.getLogger(__name__)


def _build_tree_sync(md_path: str) -> Dict[str, Any]:
    """Synchronous tree build — runs in thread (makes LLM calls)."""
    from pageindex import run_pipeline

    provider = settings.provider.lower()
    if provider == "openai":
        os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
    elif provider == "gemini":
        os.environ.setdefault("GOOGLE_API_KEY", settings.gemini_api_key)

    tree = run_pipeline(md_path=md_path, model=settings.model)
    logger.info("PageIndex tree built: %s", md_path)
    return tree


async def build_tree(md_path: str) -> Dict[str, Any]:
    """Async wrapper for tree build (LLM calls are I/O-bound but library is sync)."""
    return await asyncio.to_thread(_build_tree_sync, md_path)


def flatten_nodes(tree: Dict[str, Any], parent_id: str = None) -> List[Dict[str, Any]]:
    """Recursively flatten tree into a flat list of nodes."""
    nodes = []
    node = {
        "node_id": tree.get("node_id", ""),
        "title": tree.get("title", ""),
        "summary": tree.get("summary", ""),
        "start_index": tree.get("start_index", 0),
        "end_index": tree.get("end_index", 0),
        "parent_id": parent_id,
    }
    nodes.append(node)

    for child in tree.get("nodes", []):
        nodes.extend(flatten_nodes(child, parent_id=node["node_id"]))

    return nodes


def extract_bbox_from_content(content: str) -> Tuple[List[int], List[Dict]]:
    """Extract page numbers and bboxes from HTML comments embedded in node content."""
    pattern = r'<!-- meta:(.*?) -->'
    matches = re.findall(pattern, content)

    pages = set()
    bboxes = []
    for m in matches:
        try:
            meta = json.loads(m)
            pages.add(meta["page"])
            if meta.get("bbox"):
                bboxes.append({"page": meta["page"], "bbox": meta["bbox"]})
        except (json.JSONDecodeError, KeyError):
            continue

    return sorted(pages), bboxes


async def save_to_db(
    db: AsyncSession,
    doc_id: str,
    file_name: str,
    minio_key: str,
    user_id: str,
    tree: Dict,
    markdown_text: str,
    bucket: str = "documents",
) -> int:
    """
    Save document, tree, and nodes to PostgreSQL via async SQLAlchemy ORM.
    Extracts page/bbox metadata from HTML comments in node content.
    """
    # Upsert document
    doc = await db.get(Document, doc_id)
    if doc:
        doc.file_name = file_name
        doc.minio_key = minio_key
        doc.user_id = user_id
        doc.status = "completed"
    else:
        doc = Document(
            doc_id=doc_id, file_name=file_name, minio_key=minio_key,
            bucket=bucket, user_id=user_id, status="completed",
        )
        db.add(doc)

    # Upsert tree
    tree_obj = await db.get(DocumentTree, doc_id)
    if tree_obj:
        tree_obj.tree_json = tree
    else:
        tree_obj = DocumentTree(doc_id=doc_id, tree_json=tree)
        db.add(tree_obj)

    await db.flush()

    # Flatten and upsert nodes
    flat_nodes = flatten_nodes(tree)
    md_lines = markdown_text.split("\n")

    for node in flat_nodes:
        start = node["start_index"]
        end = node["end_index"]
        content = "\n".join(md_lines[start:end + 1]) if end < len(md_lines) else "\n".join(md_lines[start:])
        page_list, bbox_list = extract_bbox_from_content(content)

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
                node_id=node["node_id"], doc_id=doc_id,
                parent_id=node.get("parent_id"),
                title=node["title"], summary=node.get("summary", ""),
                content=content, start_index=start, end_index=end,
                pages=page_list, bboxes=bbox_list,
            ))

    await db.flush()
    logger.info("Saved to DB: doc_id=%s, %d nodes", doc_id, len(flat_nodes))
    return len(flat_nodes)
