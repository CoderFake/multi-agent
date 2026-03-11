"""Embedding service using sentence-transformers.

Usage:
    from app.utils.embeddings import embed_query, embed_texts
"""

import logging

from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Get or load the embedding model (lazy singleton)."""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info(f"Embedding model loaded: dim={_model.get_sentence_embedding_dimension()}")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors.
    """
    model = get_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Generate embedding for a single query.

    Args:
        query: Query text to embed.

    Returns:
        Embedding vector.
    """
    model = get_model()
    embedding = model.encode(query, normalize_embeddings=True)
    return embedding.tolist()

