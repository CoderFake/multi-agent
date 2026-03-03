"""
Async PaddleOCR service — PP-StructureV3 layout detection + OCR.
CPU-bound work runs via asyncio.to_thread to avoid blocking the event loop.
Extracts structured blocks with bbox, page_index, layout_type.
Assembles into Markdown with embedded bbox metadata in HTML comments.
"""

import asyncio
import json
import logging
import os
from typing import Tuple, List, Dict, Any

from app.config.settings import settings

logger = logging.getLogger(__name__)

_pipeline = None


def _get_pipeline():
    """Lazy-init PP-StructureV3 (heavy model load, ~2-5s first call)."""
    global _pipeline
    if _pipeline is None:
        from paddleocr import PPStructureV3
        _pipeline = PPStructureV3()
        logger.info("PP-StructureV3 initialized (device=%s)", settings.ocr_device)
    return _pipeline


def _run_ocr_sync(file_path: str) -> list:
    """Synchronous OCR — called in thread."""
    pipeline = _get_pipeline()
    result = pipeline.predict(file_path)
    logger.info("OCR completed: %d pages", len(result))
    return result


def _assemble_markdown(ocr_result: list, minio_key: str) -> Tuple[str, List[Dict]]:
    """
    Assemble PP-StructureV3 output into structured Markdown.

    - Heading hierarchy based on layout_type + font size
    - bbox metadata embedded as HTML comments for traceability
    - Returns (markdown_string, bbox_index)
    """
    lines: List[str] = []
    bbox_index: List[Dict] = []

    for page_idx, page in enumerate(ocr_result):
        sorted_blocks = sorted(
            page,
            key=lambda x: (x.get("bbox", [0, 0])[1], x.get("bbox", [0, 0])[0]),
        )

        for block in sorted_blocks:
            layout_type = block.get("layout_type", "text")
            text = block.get("text", "").strip()
            bbox = block.get("bbox")

            if not text and layout_type not in ("table", "figure"):
                continue

            block_meta = {
                "page": page_idx,
                "bbox": bbox,
                "layout_type": layout_type,
                "minio_key": minio_key,
            }
            bbox_index.append(block_meta)

            meta_comment = f'<!-- meta:{json.dumps(block_meta, ensure_ascii=False)} -->'

            if layout_type == "title":
                font_size = block.get("font_size", 12)
                level = "#" if font_size >= 18 else "##"
                lines.append(f"\n{meta_comment}\n{level} {text}\n")
            elif layout_type == "table":
                html_content = block.get("html", text)
                lines.append(f"\n{meta_comment}\n{html_content}\n")
            elif layout_type == "figure_caption":
                lines.append(f"\n{meta_comment}\n> {text}\n")
            elif layout_type == "formula":
                lines.append(f"\n{meta_comment}\n```\n{text}\n```\n")
            elif text:
                lines.append(f"\n{meta_comment}\n{text}\n")

    markdown = "\n".join(lines)
    logger.info("Assembled markdown: %d chars, %d blocks", len(markdown), len(bbox_index))
    return markdown, bbox_index


def _process_file_sync(file_path: str, minio_key: str) -> Tuple[str, str, List[Dict]]:
    """Synchronous pipeline — runs in thread."""
    ocr_result = _run_ocr_sync(file_path)
    markdown, bbox_index = _assemble_markdown(ocr_result, minio_key)

    os.makedirs(settings.temp_dir, exist_ok=True)
    md_path = os.path.join(settings.temp_dir, f"{os.path.basename(file_path)}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    logger.info("OCR pipeline complete: %s → %s", file_path, md_path)
    return markdown, md_path, bbox_index


async def process_file_async(
    file_path: str, minio_key: str,
) -> Tuple[str, str, List[Dict]]:
    """
    Async wrapper — offloads CPU-heavy OCR to a thread.
    Returns (markdown_text, md_file_path, bbox_index).
    """
    return await asyncio.to_thread(_process_file_sync, file_path, minio_key)
