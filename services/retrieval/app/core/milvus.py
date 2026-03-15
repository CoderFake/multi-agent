"""Milvus collection management with access control.

Collection naming: {org_subdomain}_{agent_codename}
Schema includes access control fields: org_id, group_ids, access_type.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusClient,
    connections,
    utility,
)

from app.config.settings import settings

logger = logging.getLogger(__name__)

_connected = False


def connect_milvus() -> None:
    """Connect to Milvus server."""
    global _connected
    if _connected:
        return
    connections.connect(
        alias="default",
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT,
    )
    _connected = True
    logger.info("Milvus connected: %s:%s", settings.MILVUS_HOST, settings.MILVUS_PORT)


def disconnect_milvus() -> None:
    """Disconnect from Milvus."""
    global _connected
    if _connected:
        connections.disconnect("default")
        _connected = False
        logger.info("Milvus disconnected")


def get_milvus_client() -> MilvusClient:
    """Get a MilvusClient instance (backward-compatible helper).

    Used by file_service and health check routes.
    """
    connect_milvus()
    return MilvusClient(
        uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}",
    )


def sanitize_collection_name(name: str) -> str:
    """Ensure collection name is Milvus-safe (no hyphens, alphanumeric + underscore)."""
    safe = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if safe and safe[0].isdigit():
        safe = f"c_{safe}"
    return safe


def get_collection_name(org_subdomain: str, agent_code: str) -> str:
    """Build Milvus collection name: {org_subdomain}_{agent_code}."""
    raw = f"{org_subdomain}_{agent_code}" if agent_code else org_subdomain
    return sanitize_collection_name(raw)


def _build_schema() -> CollectionSchema:
    """Build the Milvus collection schema with access control fields."""
    fields = [
        FieldSchema("chunk_id", DataType.VARCHAR, max_length=256, is_primary=True),
        FieldSchema("document_id", DataType.VARCHAR, max_length=64),
        FieldSchema("folder_id", DataType.VARCHAR, max_length=64),
        FieldSchema("org_id", DataType.VARCHAR, max_length=64),
        FieldSchema("access_type", DataType.VARCHAR, max_length=20),
        FieldSchema("group_ids", DataType.VARCHAR, max_length=2048),
        FieldSchema("file_name", DataType.VARCHAR, max_length=512),
        FieldSchema("text", DataType.VARCHAR, max_length=65535),
        FieldSchema("chunk_index", DataType.INT64),
        FieldSchema("page", DataType.INT32),
        FieldSchema("layout_type", DataType.VARCHAR, max_length=64),
        FieldSchema("section_url", DataType.VARCHAR, max_length=2048),
        FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=settings.EMBEDDING_DIMENSION),
    ]
    return CollectionSchema(fields, description="Knowledge base with access control")


def ensure_collection(collection_name: str) -> Collection:
    """Get or create a Milvus collection with the standard schema."""
    connect_milvus()

    if not utility.has_collection(collection_name):
        schema = _build_schema()
        col = Collection(collection_name, schema)
        col.create_index(
            "embedding",
            {
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": settings.MILVUS_NLIST},
            },
        )
        logger.info("Milvus collection created: %s", collection_name)
    else:
        col = Collection(collection_name)

    col.load()
    return col


def insert_chunks(
    collection_name: str,
    chunk_ids: List[str],
    document_ids: List[str],
    folder_ids: List[str],
    org_ids: List[str],
    access_types: List[str],
    group_ids_list: List[str],
    file_names: List[str],
    texts: List[str],
    chunk_indices: List[int],
    pages: List[int],
    layout_types: List[str],
    section_urls: List[str],
    embeddings: List[List[float]],
) -> None:
    """Insert chunks into Milvus collection."""
    col = ensure_collection(collection_name)
    data = [
        chunk_ids,
        document_ids,
        folder_ids,
        org_ids,
        access_types,
        group_ids_list,
        file_names,
        texts,
        chunk_indices,
        pages,
        layout_types,
        section_urls,
        embeddings,
    ]
    col.insert(data)
    col.flush()
    logger.info("Milvus inserted %d chunks into %s", len(chunk_ids), collection_name)


def search_chunks(
    collection_name: str,
    query_embedding: List[float],
    org_id: str,
    user_group_ids: List[str] | None = None,
    user_role: str = "member",
    top_k: int | None = None,
) -> List[dict]:
    """
    Search Milvus with access control filter.

    - owner/admin → full org access
    - member → public OR group_ids match
    """
    if top_k is None:
        top_k = settings.DEFAULT_TOP_K

    col = ensure_collection(collection_name)

    # Build expression based on role
    if user_role in ("owner", "admin"):
        expr = f'org_id == "{org_id}"'
    else:
        expr = f'org_id == "{org_id}" AND access_type == "public"'
        if user_group_ids:
            group_filters = " OR ".join(
                f'group_ids like "%{gid}%"' for gid in user_group_ids
            )
            expr = f'org_id == "{org_id}" AND (access_type == "public" OR {group_filters})'

    results = col.search(
        data=[query_embedding],
        anns_field="embedding",
        param={
            "metric_type": "COSINE",
            "params": {"nprobe": settings.MILVUS_NPROBE},
        },
        limit=top_k,
        expr=expr,
        output_fields=[
            "document_id", "folder_id", "text", "file_name",
            "chunk_index", "page", "layout_type", "section_url",
            "access_type", "group_ids",
        ],
    )

    hits = []
    for hit in results[0]:
        entity = hit.entity
        hits.append({
            "text": entity.get("text", ""),
            "score": hit.score,
            "document_id": entity.get("document_id", ""),
            "folder_id": entity.get("folder_id", ""),
            "file_name": entity.get("file_name", ""),
            "chunk_index": entity.get("chunk_index", 0),
            "page": entity.get("page", 0),
            "layout_type": entity.get("layout_type", "text"),
            "section_url": entity.get("section_url", ""),
            "access_type": entity.get("access_type", "public"),
            "group_ids": entity.get("group_ids", ""),
        })
    return hits


def delete_document_chunks(collection_name: str, document_id: str) -> None:
    """Delete all chunks for a document."""
    col = ensure_collection(collection_name)
    col.delete(f'document_id == "{document_id}"')
    logger.info("Deleted chunks for document %s from %s", document_id, collection_name)
