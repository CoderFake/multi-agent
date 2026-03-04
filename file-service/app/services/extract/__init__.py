"""
Extract package — public API.

Usage:
    from app.services.extract import get_extractor, ExtractResult, BlockMeta

The extract module is PURE: no database, no network side effects.
All IO side effects (DB writes, MinIO uploads) live in services/document.py.
"""

from .base import BlockMeta, ExtractResult, BaseExtractor, VISUAL_BLOCK_TYPES
from .docling import DoclingExtractor
from .hybrid import HybridExtractor, get_extractor
from .paddleocr import PPStructureV3Extractor
from .pageindex import build_tree, flatten_nodes, extract_bbox_from_content

__all__ = [
    "BaseExtractor",
    "BlockMeta",
    "ExtractResult",
    "HybridExtractor",
    "VISUAL_BLOCK_TYPES",
    "get_extractor",
    "build_tree",
    "flatten_nodes",
    "extract_bbox_from_content",
]
