"""
Hybrid extractor — routes to Docling or PP-StructureV3 based on file type
and optional confidence threshold.

Routing table:
  .docx / .pptx / .xlsx / .html    →  Docling only
  .pdf (digital / native text)      →  Docling → fallback PP-StructureV3
  .pdf (scanned / image-heavy)      →  PP-StructureV3 directly
  .png / .jpg / .jpeg / .tiff / ... →  PP-StructureV3 only

Scanned PDF detection: if Docling returns < MIN_BLOCK_DENSITY blocks per page
the file is treated as scanned and re-processed with PP-StructureV3.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.services.extract.base import BaseExtractor, ExtractResult
from app.services.extract.docling import DoclingExtractor
from app.services.extract.paddleocr import PPStructureV3Extractor
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Extensions where Docling is the only option (it handles non-PDF natively)
DOCLING_ONLY_EXTS = {".docx", ".pptx", ".xlsx", ".html", ".htm", ".eml"}

# Extensions where PaddleOCR is always used (raster images)
PADDLE_ONLY_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}


def _ext(file_path: str) -> str:
    return "." + file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""


class HybridExtractor(BaseExtractor):
    """
    Routes extraction to Docling or PP-StructureV3 based on file type.
    For PDFs, tries Docling first and falls back to PaddleOCR if the result
    looks like a scanned document (too few blocks per page).
    """

    def __init__(self):
        self._docling: Optional[DoclingExtractor] = None
        self._paddle: Optional[PPStructureV3Extractor] = None

    @property
    def name(self) -> str:
        return "hybrid"

    def _get_docling(self) -> DoclingExtractor:
        if self._docling is None:
            self._docling = DoclingExtractor()
        return self._docling

    def _get_paddle(self) -> PPStructureV3Extractor:
        if self._paddle is None:
            self._paddle = PPStructureV3Extractor()
        return self._paddle

    async def extract(self, file_path: str, minio_key: str) -> ExtractResult:
        ext = _ext(file_path)

        # ── Docling-only formats ────────────────────────────────────────
        if ext in DOCLING_ONLY_EXTS:
            logger.info("[Hybrid] %s → Docling (office format)", file_path)
            result = await self._get_docling().extract(file_path, minio_key)
            result.engine = "hybrid/docling"
            return result

        # ── Raster image formats ────────────────────────────────────────
        if ext in PADDLE_ONLY_EXTS:
            logger.info("[Hybrid] %s → PP-StructureV3 (raster image)", file_path)
            result = await self._get_paddle().extract(file_path, minio_key)
            result.engine = "hybrid/paddleocr"
            return result

        # ── PDF: try Docling first ──────────────────────────────────────
        logger.info("[Hybrid] %s → trying Docling first (PDF)", file_path)
        try:
            docling_result = await self._get_docling().extract(file_path, minio_key)
            page_count = max(docling_result.page_count, 1)
            block_density = len(docling_result.blocks) / page_count

            if block_density >= settings.min_block_density:
                logger.info(
                    "[Hybrid] Docling OK (%.1f blocks/page) → using Docling result",
                    block_density,
                )
                docling_result.engine = "hybrid/docling"
                return docling_result

            logger.warning(
                "[Hybrid] Docling low density (%.1f blocks/page) → fallback PP-StructureV3",
                block_density,
            )
        except Exception as e:
            logger.warning("[Hybrid] Docling failed (%s) → fallback PP-StructureV3", e)

        # ── Fallback: PP-StructureV3 ────────────────────────────────────
        paddle_result = await self._get_paddle().extract(file_path, minio_key)
        paddle_result.engine = "hybrid/paddleocr"
        return paddle_result


# Module-level singleton (lazy instantiated)
_hybrid_extractor: Optional[HybridExtractor] = None


def get_extractor() -> HybridExtractor:
    global _hybrid_extractor
    if _hybrid_extractor is None:
        _hybrid_extractor = HybridExtractor()
    return _hybrid_extractor
