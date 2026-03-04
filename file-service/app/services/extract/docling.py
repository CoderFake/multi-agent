"""
Docling extractor — wraps IBM's Docling document conversion pipeline.
Pure extraction: file in → ExtractResult out. No DB, no network.

Best for:
  - Office documents: DOCX, PPTX, XLSX
  - Digital (native) PDFs — fast, accurate
  - HTML pages
  - Clean English/European text

Falls back to PP-StructureV3 via HybridExtractor if confidence is low.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import List, Tuple

from app.config.settings import settings
from app.services.extract.base import (
    BaseExtractor,
    BlockMeta,
    ExtractResult,
    DOCLING_LABEL_MAP,
    VISUAL_BLOCK_TYPES,
)

logger = logging.getLogger(__name__)


def _canonical_type(docling_label: str) -> str:
    return DOCLING_LABEL_MAP.get(docling_label, "text")


def _parse_docling_document(doc, minio_key: str) -> Tuple[List[BlockMeta], str, int]:
    """
    Convert a Docling DocumentConverter result into BlockMeta list + markdown.
    Uses Docling's export_to_markdown() for the full document string,
    and iterates DocItems for per-block metadata.
    """
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import DocumentConverter

    # Export full markdown
    markdown = doc.export_to_markdown()
    blocks: List[BlockMeta] = []
    page_count = 0

    for item, level in doc.iterate_items():
        label = getattr(item, "label", "")
        layout_type = _canonical_type(str(label))

        # Get page + bbox from prov (provenance)
        page = 0
        bbox: List[float] = []
        if hasattr(item, "prov") and item.prov:
            prov = item.prov[0]
            page = getattr(prov, "page_no", 1) - 1  # convert 1-indexed → 0-indexed
            page_count = max(page_count, page + 1)
            if hasattr(prov, "bbox"):
                b = prov.bbox
                bbox = [b.l, b.t, b.r, b.b]

        # Extract text content
        text = ""
        html = ""
        if hasattr(item, "text"):
            text = item.text or ""
        elif hasattr(item, "export_to_markdown"):
            try:
                text = item.export_to_markdown(doc) or ""
            except TypeError:
                text = item.export_to_markdown() or ""

        # Table → HTML
        if layout_type == "table" and hasattr(item, "export_to_html"):
            try:
                html = item.export_to_html(doc) or ""
                text = item.export_to_markdown(doc) or text
            except TypeError:
                html = item.export_to_html() or ""
                text = item.export_to_markdown() or text

        if not text and layout_type not in VISUAL_BLOCK_TYPES:
            continue

        blocks.append(BlockMeta(
            page=page,
            bbox=bbox,
            layout_type=layout_type,
            text=text,
            html=html,
            confidence=1.0,
            label=str(label),
        ))

    return blocks, markdown, page_count


def _embed_bbox_comments(markdown: str, blocks: List[BlockMeta], minio_key: str) -> str:
    """
    Docling markdown doesn't embed bbox HTML comments — we annotate the start
    of the markdown with a JSON index block that retrieval.py can consume.
    Full block metadata is stored in PostgreSQL bboxes column; the markdown
    comments are lightweight page refs only.
    """
    header_lines = []
    for block in blocks:
        if block.bbox:
            meta = {
                "page": block.page,
                "bbox": block.bbox,
                "layout_type": block.layout_type,
                "minio_key": minio_key,
            }
            header_lines.append(f'<!-- meta:{json.dumps(meta, ensure_ascii=False)} -->')

    if header_lines:
        return "\n".join(header_lines) + "\n\n" + markdown
    return markdown


def _process_sync(file_path: str, minio_key: str) -> ExtractResult:
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(file_path)
    doc = result.document

    blocks, markdown_raw, page_count = _parse_docling_document(doc, minio_key)
    markdown = _embed_bbox_comments(markdown_raw, blocks, minio_key)

    os.makedirs(settings.temp_dir, exist_ok=True)
    md_path = os.path.join(settings.temp_dir, f"{os.path.basename(file_path)}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    logger.info("Docling done: %s → %d blocks, %d pages", file_path, len(blocks), page_count)
    return ExtractResult(
        markdown=markdown,
        md_path=md_path,
        blocks=blocks,
        engine="docling",
        page_count=page_count,
    )


class DoclingExtractor(BaseExtractor):
    """Docling-based document extractor (PDF/DOCX/PPTX/XLSX/HTML)."""

    @property
    def name(self) -> str:
        return "docling"

    async def extract(self, file_path: str, minio_key: str) -> ExtractResult:
        """Async wrapper — Docling runs synchronously, offload to thread."""
        return await asyncio.to_thread(_process_sync, file_path, minio_key)
