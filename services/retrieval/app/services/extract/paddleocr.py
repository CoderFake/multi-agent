"""
PP-StructureV3 extractor — wraps PaddleOCR's layout pipeline.
Pure extraction: file in → ExtractResult out. No DB, no network.

Best for:
  - Scanned PDFs / image-only PDFs
  - Vietnamese, Chinese, Japanese text
  - Complex tables, math formulas
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from paddleocr import PPStructureV3 as _PPStructureV3

from app.config.settings import settings
from app.services.extract.base import (
    BaseExtractor,
    BlockMeta,
    ExtractResult,
    VISUAL_BLOCK_TYPES,
)

logger = logging.getLogger(__name__)

_pipeline: "_PPStructureV3 | None" = None


def _get_pipeline():
    """Lazy-init PP-StructureV3 — heavy model load, ~2-5s first call."""
    global _pipeline
    if _pipeline is None:
        from paddleocr import PPStructureV3
        _pipeline = PPStructureV3(use_chart_parsing=False)
        logger.info("PP-StructureV3 initialized (device=%s)", settings.OCR_DEVICE)
    return _pipeline


def _run_ocr_sync(file_path: str) -> list:
    pipeline = _get_pipeline()
    result = pipeline.predict(file_path)
    logger.info("PP-StructureV3 completed: %d pages", len(result))
    return result


def _parse_blocks(ocr_result: list, storage_key: str) -> Tuple[List[BlockMeta], int]:
    """Parse PP-StructureV3 output into BlockMeta list."""
    blocks: List[BlockMeta] = []
    for page_idx, page in enumerate(ocr_result):
        for block in page:
            layout_type = block.get("layout_type", "text")
            text = block.get("text", "").strip()
            bbox = block.get("bbox") or []
            html = block.get("html", "")
            latex = block.get("latex", "")

            if not text and layout_type not in VISUAL_BLOCK_TYPES:
                continue

            blocks.append(BlockMeta(
                page=page_idx,
                bbox=bbox,
                layout_type=layout_type,
                text=text,
                html=html,
                latex=latex,
                confidence=block.get("score", 1.0),
                label=layout_type,
            ))
    return blocks, len(ocr_result)


def _assemble_markdown(blocks: List[BlockMeta], storage_key: str) -> str:
    """Assemble blocks into Markdown with embedded bbox metadata comments."""
    lines: list[str] = []

    sorted_blocks = sorted(
        blocks,
        key=lambda b: (b.page, b.bbox[1] if b.bbox else 0, b.bbox[0] if b.bbox else 0),
    )

    for block in sorted_blocks:
        meta = {
            "page": block.page,
            "bbox": block.bbox,
            "layout_type": block.layout_type,
            "storage_key": storage_key,
        }
        comment = f'<!-- meta:{json.dumps(meta, ensure_ascii=False)} -->'

        if block.layout_type == "title":
            lines.append(f"\n{comment}\n# {block.text}\n")
        elif block.layout_type == "table":
            content = block.html or block.text
            lines.append(f"\n{comment}\n{content}\n")
        elif block.layout_type == "figure":
            lines.append(f"\n{comment}\n![figure]()\n")
        elif block.layout_type == "formula":
            body = block.latex or block.text
            lines.append(f"\n{comment}\n$$\n{body}\n$$\n")
        elif block.layout_type == "caption":
            lines.append(f"\n{comment}\n> {block.text}\n")
        elif block.text:
            lines.append(f"\n{comment}\n{block.text}\n")

    return "\n".join(lines)


def _process_sync(file_path: str, storage_key: str) -> ExtractResult:
    ocr_result = _run_ocr_sync(file_path)
    blocks, page_count = _parse_blocks(ocr_result, storage_key)
    markdown = _assemble_markdown(blocks, storage_key)

    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    md_path = os.path.join(settings.TEMP_DIR, f"{os.path.basename(file_path)}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    logger.info("PP-StructureV3 done: %s → %d blocks, %d pages", file_path, len(blocks), page_count)
    return ExtractResult(
        markdown=markdown,
        md_path=md_path,
        blocks=blocks,
        engine="paddleocr",
        page_count=page_count,
    )


class PPStructureV3Extractor(BaseExtractor):
    """PP-StructureV3 based document extractor."""

    @property
    def name(self) -> str:
        return "paddleocr"

    async def extract(self, file_path: str, storage_key: str) -> ExtractResult:
        """Async wrapper — CPU-heavy OCR runs in thread pool."""
        return await asyncio.to_thread(_process_sync, file_path, storage_key)
