"""
Extract package — document content extraction.

Usage:
    from app.services.extract import get_extractor, ExtractResult, BlockMeta

Pure extraction: file in → ExtractResult out. No database, no network.
"""

from .base import BlockMeta, ExtractResult, BaseExtractor, VISUAL_BLOCK_TYPES
from .hybrid import HybridExtractor, get_extractor

__all__ = [
    "BaseExtractor",
    "BlockMeta",
    "ExtractResult",
    "HybridExtractor",
    "VISUAL_BLOCK_TYPES",
    "get_extractor",
]
