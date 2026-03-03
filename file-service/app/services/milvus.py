"""
Milvus RAG service — knowledge base for agent reasoning.

Collection: agent_knowledge
Each chunk = one DocumentNode (title + summary + content).
Chunk metadata stores doc_id, node_id, page, bbox, layout_type, section_url.

Used by:
  - gRPC KnowledgeSearch handler (searches all user docs)
  - gRPC ProcessDocument handler (upserts chunks after extraction)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.config.settings import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = settings.milvus_collection
EMBEDDING_DIM = settings.milvus_embedding_dim

# Embedding model per provider
_EMBED_MODELS = {
    "openai": "text-embedding-3-small",
    "gemini": "models/text-embedding-004",
    "ollama": "nomic-embed-text",
}


@dataclass
class ChunkDoc:
    """A document chunk ready for Milvus insertion."""
    chunk_id: str          # f"{doc_id}::{node_id}"
    doc_id: str
    node_id: str
    user_id: str
    node_title: str
    text: str              # title + summary + content concatenated
    page: int = 0
    bbox: List[float] = field(default_factory=list)
    layout_type: str = "text"
    section_url: str = ""  # MinIO presigned URL for visual section


@dataclass
class ChunkResult:
    """A search result from Milvus."""
    text: str
    score: float
    doc_id: str
    node_id: str
    node_title: str
    page: int
    bbox: List[float]
    layout_type: str
    section_url: str


# ── Embedding ──────────────────────────────────────────────────────────

_embed_model = None


def _get_embed_func():
    """Return a synchronous embedding function for the configured provider."""
    global _embed_model
    if _embed_model is not None:
        return _embed_model

    provider = settings.provider.lower()
    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        model = _EMBED_MODELS["openai"]

        def embed_fn(texts: List[str]) -> List[List[float]]:
            resp = client.embeddings.create(model=model, input=texts)
            return [d.embedding for d in resp.data]

        _embed_model = embed_fn
    elif provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        model = _EMBED_MODELS["gemini"]

        def embed_fn(texts: List[str]) -> List[List[float]]:
            return [genai.embed_content(model=model, content=t)["embedding"] for t in texts]

        _embed_model = embed_fn
    else:
        # Ollama
        import requests
        model = _EMBED_MODELS["ollama"]

        def embed_fn(texts: List[str]) -> List[List[float]]:
            return [
                requests.post(
                    f"{settings.ollama_base_url}/api/embeddings",
                    json={"model": model, "prompt": t},
                ).json()["embedding"]
                for t in texts
            ]

        _embed_model = embed_fn

    return _embed_model


# ── Milvus collection management ───────────────────────────────────────

_collection = None


def _get_collection():
    """Lazy-init Milvus collection, creating it if necessary."""
    global _collection
    if _collection is not None:
        return _collection

    from pymilvus import (
        Collection,
        CollectionSchema,
        DataType,
        FieldSchema,
        connections,
        utility,
    )

    connections.connect(
        alias="default",
        host=settings.milvus_host,
        port=settings.milvus_port,
    )

    if not utility.has_collection(COLLECTION_NAME):
        fields = [
            FieldSchema("chunk_id", DataType.VARCHAR, max_length=256, is_primary=True),
            FieldSchema("doc_id", DataType.VARCHAR, max_length=64),
            FieldSchema("node_id", DataType.VARCHAR, max_length=128),
            FieldSchema("user_id", DataType.VARCHAR, max_length=256),
            FieldSchema("node_title", DataType.VARCHAR, max_length=512),
            FieldSchema("text", DataType.VARCHAR, max_length=65535),
            FieldSchema("page", DataType.INT32),
            FieldSchema("bbox", DataType.VARCHAR, max_length=256),       # JSON list
            FieldSchema("layout_type", DataType.VARCHAR, max_length=64),
            FieldSchema("section_url", DataType.VARCHAR, max_length=2048),
            FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        ]
        schema = CollectionSchema(fields, description="Agent knowledge base")
        col = Collection(COLLECTION_NAME, schema)
        col.create_index(
            "embedding",
            {
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": settings.milvus_nlist},
            },
        )
        logger.info("Milvus collection created: %s", COLLECTION_NAME)
    else:
        col = Collection(COLLECTION_NAME)
        col.load()

    _collection = col
    return _collection


# ── Sync helpers (run in thread) ───────────────────────────────────────

def _upsert_sync(chunks: List[ChunkDoc]) -> None:
    import json
    col = _get_collection()
    embed_fn = _get_embed_func()

    texts = [c.text for c in chunks]
    embeddings = embed_fn(texts)

    data = [
        [c.chunk_id for c in chunks],
        [c.doc_id for c in chunks],
        [c.node_id for c in chunks],
        [c.user_id for c in chunks],
        [c.node_title[:511] for c in chunks],
        [c.text[:65534] for c in chunks],
        [c.page for c in chunks],
        [json.dumps(c.bbox)[:255] for c in chunks],
        [c.layout_type for c in chunks],
        [c.section_url[:2047] for c in chunks],
        embeddings,
    ]
    col.upsert(data)
    col.flush()
    logger.info("Milvus upsert: %d chunks", len(chunks))


def _search_sync(query: str, user_id: str, top_k: int, filter_doc_ids: List[str]) -> List[Dict]:
    import json
    col = _get_collection()
    embed_fn = _get_embed_func()

    query_emb = embed_fn([query])[0]

    expr = f'user_id == "{user_id}"'
    if filter_doc_ids:
        ids_quoted = ", ".join(f'"{d}"' for d in filter_doc_ids)
        expr += f' && doc_id in [{ids_quoted}]'

    results = col.search(
        data=[query_emb],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": settings.milvus_nprobe}},
        limit=top_k,
        expr=expr,
        output_fields=["doc_id", "node_id", "node_title", "text", "page", "bbox", "layout_type", "section_url"],
    )

    hits = []
    for hit in results[0]:
        entity = hit.entity
        hits.append({
            "text": entity.get("text", ""),
            "score": hit.score,
            "doc_id": entity.get("doc_id", ""),
            "node_id": entity.get("node_id", ""),
            "node_title": entity.get("node_title", ""),
            "page": entity.get("page", 0),
            "bbox": json.loads(entity.get("bbox", "[]")),
            "layout_type": entity.get("layout_type", "text"),
            "section_url": entity.get("section_url", ""),
        })
    return hits


def _delete_sync(doc_id: str) -> None:
    col = _get_collection()
    col.delete(f'doc_id == "{doc_id}"')
    logger.info("Milvus deleted chunks for doc_id=%s", doc_id)


# ── Public async API ───────────────────────────────────────────────────

class MilvusService:
    """Async wrapper around synchronous Milvus operations."""

    async def upsert_chunks(self, chunks: List[ChunkDoc]) -> None:
        if not chunks:
            return
        await asyncio.to_thread(_upsert_sync, chunks)

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 8,
        filter_doc_ids: Optional[List[str]] = None,
    ) -> List[ChunkResult]:
        raw = await asyncio.to_thread(
            _search_sync, query, user_id, top_k, filter_doc_ids or []
        )
        return [ChunkResult(**r) for r in raw]

    async def delete_by_doc(self, doc_id: str) -> None:
        await asyncio.to_thread(_delete_sync, doc_id)


def nodes_to_chunks(
    flat_nodes: List[Dict],
    doc_id: str,
    user_id: str,
    bboxes_map: Dict[str, Any],   # node_id → list of bbox dicts (from DocumentNodes)
) -> List[ChunkDoc]:
    """Convert flat PageIndex nodes → ChunkDoc list for Milvus insertion."""
    chunks = []
    for node in flat_nodes:
        node_id = node["node_id"]
        bboxes = bboxes_map.get(node_id, [])
        # Use first visual block's section_url for the chunk
        first_visual = next(
            (b for b in bboxes if b.get("layout_type") in ("table", "figure", "formula")),
            None,
        )

        # Build text: title + summary + content preview
        text_parts = [node.get("title", ""), node.get("summary", "")]
        content = node.get("content", "")
        if content:
            # Keep first 2000 chars — enough context, keeps Milvus insertions lean
            text_parts.append(content[:2000])
        text = "\n".join(p for p in text_parts if p)

        chunks.append(ChunkDoc(
            chunk_id=f"{doc_id}::{node_id}",
            doc_id=doc_id,
            node_id=node_id,
            user_id=user_id,
            node_title=node.get("title", ""),
            text=text,
            page=bboxes[0]["page"] if bboxes else 0,
            bbox=bboxes[0]["bbox"] if bboxes else [],
            layout_type=first_visual["layout_type"] if first_visual else "text",
            section_url=first_visual.get("minio_key", "") if first_visual else "",
        ))
    return chunks


milvus_service = MilvusService()
