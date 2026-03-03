"""
PageIndex tree construction helpers — PURE, no DB, no SQLAlchemy.

These helpers take a markdown file and return a tree structure suitable
for LLM-assisted hierarchical retrieval. Database persistence is handled
by services/document.py.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Tuple

from app.config.settings import settings

logger = logging.getLogger(__name__)


# ── Tree construction ──────────────────────────────────────────────────

def _build_tree_sync(md_path: str) -> Dict[str, Any]:
    """Synchronous tree build — runs in thread (makes LLM calls via pageindex)."""
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
    """Async wrapper — LLM calls are sync, offload to thread pool."""
    return await asyncio.to_thread(_build_tree_sync, md_path)


# ── Tree helpers ───────────────────────────────────────────────────────

def flatten_nodes(tree: Dict[str, Any], parent_id: str | None = None) -> List[Dict[str, Any]]:
    """Recursively flatten a PageIndex tree into a flat node list."""
    nodes: List[Dict[str, Any]] = []
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
    """
    Extract page numbers and bboxes from HTML comments embedded in node content.
    Comments are of the form: <!-- meta:{...} -->
    """
    pattern = r'<!-- meta:(.*?) -->'
    matches = re.findall(pattern, content)

    pages: set[int] = set()
    bboxes: List[Dict] = []
    for m in matches:
        try:
            meta = json.loads(m)
            pages.add(meta["page"])
            if meta.get("bbox"):
                bboxes.append({
                    "page": meta["page"],
                    "bbox": meta["bbox"],
                    "layout_type": meta.get("layout_type", "text"),
                    "minio_key": meta.get("minio_key", ""),
                })
        except (json.JSONDecodeError, KeyError):
            continue

    return sorted(pages), bboxes
