"""Milvus client wrapper for vector operations.

Usage:
    from app.core.milvus import get_milvus_client, ensure_collection, close_milvus
"""

import logging

from pymilvus import MilvusClient, connections

from app.config import settings

logger = logging.getLogger(__name__)

_client: MilvusClient | None = None


def get_milvus_client() -> MilvusClient:
    """Get or create Milvus client singleton."""
    global _client
    if _client is None:
        uri = settings.milvus_uri
        _client = MilvusClient(uri=uri)
        logger.info(f"Connected to Milvus at {uri}")
    return _client


def ensure_collection(collection_name: str) -> None:
    """Ensure a Milvus collection exists with the correct schema.

    Creates the collection if it doesn't exist.
    """
    from pymilvus import CollectionSchema, DataType, FieldSchema

    client = get_milvus_client()

    if client.has_collection(collection_name):
        return

    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=settings.EMBEDDING_DIMENSION),
        FieldSchema(name="team_id", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="file_name", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="chunk_index", dtype=DataType.INT64),
    ]

    schema = CollectionSchema(fields=fields, description=f"RAG collection: {collection_name}")
    client.create_collection(
        collection_name=collection_name,
        schema=schema,
    )

    # Create vector index for search
    client.create_index(
        collection_name=collection_name,
        field_name="embedding",
        index_params={
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        },
    )
    logger.info(f"Created Milvus collection: {collection_name}")


def close_milvus():
    """Close Milvus connection on shutdown."""
    global _client
    if _client is not None:
        try:
            connections.disconnect("default")
        except Exception:
            pass
        _client = None

