"""Search business logic — vector similarity search across Milvus collections.

Usage:
    from app.services.search_service import search_svc

    response = await search_svc.search(request)
"""

import logging

from app.core.milvus import get_milvus_client
from app.utils.embeddings import embed_query
from app.schemas.search import SearchRequest, SearchResponse, SearchResult

logger = logging.getLogger(__name__)


class SearchService:
    """Vector search operations against Milvus."""

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute vector similarity search across specified collections.

        1. Embeds the query text
        2. Searches each collection in parallel (future) or sequentially
        3. Merges, ranks by score, and truncates to top_k

        Returns:
            SearchResponse with ranked results.

        Raises:
            RuntimeError: If Milvus connection fails.
        """
        if not request.collection_names:
            return SearchResponse(results=[], total=0)

        query_embedding = embed_query(request.query)
        client = get_milvus_client()

        all_results: list[SearchResult] = []

        for collection_name in request.collection_names:
            if not client.has_collection(collection_name):
                logger.warning(f"Collection '{collection_name}' not found, skipping")
                continue

            hits_list = client.search(
                collection_name=collection_name,
                data=[query_embedding],
                limit=request.top_k,
                output_fields=["text", "source", "file_name", "chunk_index"],
            )

            for hits in hits_list:
                for hit in hits:
                    entity = hit.get("entity", {})
                    all_results.append(
                        SearchResult(
                            text=entity.get("text", ""),
                            source=entity.get("source", ""),
                            score=hit.get("distance", 0.0),
                            file_name=entity.get("file_name", ""),
                            chunk_index=entity.get("chunk_index", 0),
                        )
                    )

        # Rank by similarity score descending, then truncate
        all_results.sort(key=lambda r: r.score, reverse=True)
        all_results = all_results[: request.top_k]

        return SearchResponse(results=all_results, total=len(all_results))


# Module-level singleton
search_svc = SearchService()

