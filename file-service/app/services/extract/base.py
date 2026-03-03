"""
Base classes for document extraction.

Extract module is PURE — no database, no network, no SQLAlchemy.
Input: file path + minio_key (for metadata)
Output: ExtractResult (markdown, structured blocks, engine tag)
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BlockMeta:
    """
    Metadata for a single structural block in a document.
    Populated by the extractor; minio_key is filled later by document.py
    when the section crop is uploaded to MinIO.
    """
    page: int                    # 0-indexed
    bbox: List[float]            # [x0, y0, x1, y1] in points/pixels
    layout_type: str             # "text"|"title"|"table"|"figure"|"formula"|"caption"|"header"|"footer"
    text: str = ""               # plain-text content
    html: str = ""               # HTML table markup (tables only)
    latex: str = ""              # LaTeX (formulas only)
    confidence: float = 1.0      # extraction confidence 0-1
    minio_key: str = ""          # filled by document.save_document()
    # Docling-specific
    label: str = ""              # raw Docling label before normalisation


@dataclass
class ExtractResult:
    """
    Output of any BaseExtractor.
    markdown and md_path are the full document representation.
    blocks is the flat list of all structural elements with bbox/page metadata.
    engine records which extractor produced this result.
    """
    markdown: str
    md_path: str                       # temp file written by extractor
    blocks: List[BlockMeta] = field(default_factory=list)
    engine: str = "unknown"            # "paddleocr"|"docling"|"hybrid"
    page_count: int = 0


# Layout types that should be rendered as section images (uploaded to MinIO)
VISUAL_BLOCK_TYPES = {"table", "figure", "formula"}

# Mapping from Docling DocItemLabel → our canonical layout_type
DOCLING_LABEL_MAP: dict[str, str] = {
    "title": "title",
    "section_header": "title",
    "page_header": "header",
    "page_footer": "footer",
    "text": "text",
    "list_item": "text",
    "caption": "caption",
    "footnote": "text",
    "table": "table",
    "picture": "figure",
    "formula": "formula",
    "code": "text",
    "checkbox_selected": "text",
    "checkbox_unselected": "text",
}


class BaseExtractor(abc.ABC):
    """Abstract base for all document extractors."""

    @abc.abstractmethod
    async def extract(self, file_path: str, minio_key: str) -> ExtractResult:
        """
        Extract document content.
        file_path: local temp path to uploaded document
        minio_key: the MinIO key prefix used for metadata embedding
        Returns ExtractResult — NO database operations.
        """
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Short identifier for this extractor, e.g. 'paddleocr'."""
        ...
