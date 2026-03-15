"""Embedding utility using sentence-transformers.

Usage:
    from app.utils.embeddings import embed_query, embed_texts
"""

import logging
from typing import List

from app.config.settings import settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    """Load sentence-transformers model (lazy, singleton)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded: %s (dim=%d)", settings.EMBEDDING_MODEL, settings.EMBEDDING_DIMENSION)
    return _model


def embed_query(text: str) -> List[float]:
    """Embed a single query text."""
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a batch of texts."""
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [e.tolist() for e in embeddings]
