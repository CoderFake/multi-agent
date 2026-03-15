"""Search service — permission-filtered vector search.

Usage:
    from app.services.search_service import search
"""

from __future__ import annotations

import logging
import asyncio
from typing import List, Optional
from app.schemas.search import SearchResponse, SearchResult
from app.core.milvus import get_collection_name, search_chunks
from app.utils.embeddings import embed_query

logger = logging.getLogger(__name__)


async def search(
    query: str,
    org_id: str,
    org_subdomain: str,
    agent_code: str = "",
    user_group_ids: Optional[List[str]] = None,
    user_role: str = "member",
    top_k: int = 10,
) -> List[dict]:
    """
    Search for relevant document chunks with access control.

    Args:
        query: Search query text
        org_id: Organization ID
        org_subdomain: Organization subdomain for collection naming
        agent_code: Optional agent codename for collection naming
        user_group_ids: User's group IDs for access filtering
        user_role: User's org role (owner/admin/member)
        top_k: Number of results to return

    Returns:
        List of search result dicts with text, score, metadata
    """
    collection_name = get_collection_name(org_subdomain, agent_code)

    # Embed query
    query_embedding = embed_query(query)

    # Search with access control
    results = search_chunks(
        collection_name=collection_name,
        query_embedding=query_embedding,
        org_id=org_id,
        user_group_ids=user_group_ids,
        user_role=user_role,
        top_k=top_k,
    )

    logger.info(
        "Search: query=%r org=%s collection=%s results=%d",
        query[:50], org_id, collection_name, len(results),
    )
    return results


class SearchService:
    """Backward-compatible service class for routes/search.py."""

    async def search(self, request) -> dict:
        """Search across collection_names with access control.

        Uses asyncio.to_thread() because pymilvus is synchronous.
        """
    
        query_embedding = await asyncio.to_thread(embed_query, request.query)

        async def _search_one(cname: str) -> list:
            try:
                hits = await asyncio.to_thread(
                    search_chunks,
                    collection_name=cname,
                    query_embedding=query_embedding,
                    org_id=request.org_id,
                    user_group_ids=request.user_group_ids or None,
                    user_role=request.user_role,
                    top_k=request.top_k,
                )
                return [
                    SearchResult(
                        text=hit.get("text", ""),
                        source=hit.get("section_url", ""),
                        score=hit.get("score", 0.0),
                        file_name=hit.get("file_name", ""),
                        chunk_index=hit.get("chunk_index", 0),
                    )
                    for hit in hits
                ]
            except Exception as e:
                logger.warning("Search failed for collection '%s': %s", cname, e)
                return []

        # Search all collections concurrently via thread pool
        batch = await asyncio.gather(
            *[_search_one(cname) for cname in request.collection_names]
        )
        all_results = [r for group in batch for r in group]
        all_results.sort(key=lambda r: r.score, reverse=True)
        truncated = all_results[: request.top_k]

        return SearchResponse(results=truncated, total=len(truncated))


# Module-level singleton
search_svc = SearchService()
