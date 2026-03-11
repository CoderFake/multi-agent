"""Index business logic — embed and store document chunks in Milvus.

Usage:
    from app.services.index_service import index_svc

    response = await index_svc.index_documents(request)
"""

import logging

from app.core.milvus import ensure_collection, get_milvus_client
from app.utils.embeddings import embed_texts
from app.schemas.index import IndexRequest, IndexResponse

logger = logging.getLogger(__name__)


class IndexService:
    """Document indexing operations."""

    async def index_documents(self, request: IndexRequest) -> IndexResponse:
        """Embed and index document chunks into a Milvus collection.

        1. Ensures the target collection exists (creates if needed)
        2. Generates embeddings for all chunks
        3. Inserts into Milvus

        Returns:
            IndexResponse with count of indexed chunks.

        Raises:
            RuntimeError: If embedding or Milvus insertion fails.
        """
        ensure_collection(request.collection_name)
        client = get_milvus_client()

        texts = [doc.text for doc in request.documents]
        embeddings = embed_texts(texts)

        data = [
            {
                "id": doc.id,
                "text": doc.text,
                "source": doc.source,
                "embedding": emb,
                "team_id": request.team_id,
                "file_name": doc.file_name,
                "chunk_index": doc.chunk_index,
            }
            for doc, emb in zip(request.documents, embeddings)
        ]

        client.insert(collection_name=request.collection_name, data=data)
        logger.info(
            f"Indexed {len(data)} chunks into '{request.collection_name}' "
            f"(team: {request.team_id})"
        )

        return IndexResponse(indexed=len(data), collection_name=request.collection_name)


# Module-level singleton
index_svc = IndexService()

