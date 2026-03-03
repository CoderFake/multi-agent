"""
Reasoning-based retrieval using PageIndex tree search.

Pipeline (from PageIndex tutorials):
  1. Load tree JSON from DB
  2. LLM tree search → select relevant node_ids
  3. Fetch node content + bbox from DB
  4. Generate presigned URL from MinIO
  5. LLM answer synthesis with citations

Uses langchain multi-provider pattern (openai/gemini/ollama),
same as backend/routes/agent/nodes/model.py.
"""

import json
import logging
from typing import List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.document import Document, DocumentNode, DocumentTree
from app.schemas.document import BboxRef, Citation, RetrievalResponse
from app.services.minio import minio_service

logger = logging.getLogger(__name__)

_llm: BaseChatModel | None = None


def get_llm() -> BaseChatModel:
    """Get LLM based on provider setting — same pattern as backend model.py."""
    global _llm
    if _llm is not None:
        return _llm

    provider = settings.provider.lower()
    logger.info("Initializing %s model: %s", provider, settings.model)

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        _llm = ChatGoogleGenerativeAI(
            model=settings.model,
            temperature=0,
            google_api_key=settings.gemini_api_key,
        )
    elif provider == "ollama":
        from langchain_ollama import ChatOllama

        _llm = ChatOllama(
            model=settings.model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )
    else:  # openai
        from langchain_openai import ChatOpenAI

        _llm = ChatOpenAI(
            model=settings.model,
            temperature=0,
            api_key=settings.openai_api_key,
        )

    return _llm


# ── Prompts (from PageIndex tree-search tutorial) ──────────────────

TREE_SEARCH_PROMPT = """\
You are given a query and the tree structure of a document.
You need to find all nodes that are likely to contain the answer.

Query: {query}

Document tree structure: {tree_json}

Reply in the following JSON format:
{{
  "thinking": <your reasoning about which nodes are relevant>,
  "node_list": [node_id1, node_id2, ...]
}}
"""

ANSWER_PROMPT = """\
Answer the user's question using ONLY the provided document content.
Be precise and cite the section titles when relevant.

Question: {query}

Content:
{context}
"""


async def tree_search(tree_json: dict, query: str) -> List[str]:
    """
    LLM tree search — find relevant node_ids from PageIndex tree.
    Returns list of node_id strings.
    """
    llm = get_llm()

    resp = await llm.ainvoke([
        HumanMessage(content=TREE_SEARCH_PROMPT.format(
            query=query,
            tree_json=json.dumps(tree_json, ensure_ascii=False),
        ))
    ])

    try:
        result = json.loads(resp.content)
        node_ids = result.get("node_list", [])
    except json.JSONDecodeError:
        logger.warning("Failed to parse tree search response: %s", resp.content[:200])
        node_ids = []

    logger.info("Tree search: query=%r → %d nodes selected", query, len(node_ids))
    return node_ids


async def retrieve(
    db: AsyncSession, doc_id: str, query: str,
) -> RetrievalResponse:
    """
    Full retrieval pipeline:
      tree search → fetch nodes → presigned URL → answer synthesis.
    """
    # 1. Load document + tree
    doc = await db.get(Document, doc_id)
    if not doc:
        raise ValueError(f"Document {doc_id} not found")

    tree_obj = await db.get(DocumentTree, doc_id)
    if not tree_obj:
        raise ValueError(f"Tree for document {doc_id} not found")

    # 2. LLM tree search
    node_ids = await tree_search(tree_obj.tree_json, query)
    if not node_ids:
        return RetrievalResponse(
            answer="No relevant sections found in the document.",
            citations=[],
            doc_id=doc_id,
        )

    # 3. Fetch nodes from DB
    result = await db.execute(
        select(DocumentNode)
        .where(DocumentNode.doc_id == doc_id, DocumentNode.node_id.in_(node_ids))
    )
    nodes = result.scalars().all()

    if not nodes:
        return RetrievalResponse(
            answer="Selected nodes not found in the database.",
            citations=[],
            doc_id=doc_id,
        )

    # 4. Generate presigned URL
    presigned_url = await minio_service.get_presigned_url(doc.minio_key)

    # 5. Build context + citations
    context_parts = []
    citations = []
    for node in nodes:
        context_parts.append(f"[{node.title}]\n{node.content}")

        bboxes = [
            BboxRef(page=b["page"], bbox=b["bbox"])
            for b in (node.bboxes or [])
            if isinstance(b, dict) and "page" in b and "bbox" in b
        ]

        citations.append(Citation(
            node_id=node.node_id,
            title=node.title,
            pages=node.pages or [],
            bboxes=bboxes,
            source_url=presigned_url,
        ))

    # 6. LLM answer synthesis
    llm = get_llm()
    resp = await llm.ainvoke([
        SystemMessage(content="Answer using only the provided document content."),
        HumanMessage(content=ANSWER_PROMPT.format(
            query=query,
            context="\n\n".join(context_parts),
        )),
    ])

    return RetrievalResponse(
        answer=resp.content,
        citations=citations,
        doc_id=doc_id,
    )
