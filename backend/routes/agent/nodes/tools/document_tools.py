"""
Document MCP Tools Node — ChatSessionDocument + Knowledge

Two nodes integrated as LangGraph nodes:

  1. document_node:
     – PageIndex reasoning over a specific document the user uploaded
     – Returns answer + per-section citations (table/figure/formula)
     – Triggered when uploaded_doc_ids is non-empty

  2. knowledge_node:
     – Milvus semantic search across all user's indexed knowledge base
     – Returns relevant chunks + citations with section images
     – Triggered when research_mode=True

HITL pattern:
  graph.compile(interrupt_before=["document_node", "knowledge_node"])
  → graph pauses BEFORE each node; frontend shows ApprovalCard
  → on approve: graph.invoke(Command(resume=...)) → node executes
  → on reject: node is skipped (graph routes to next via Command)
"""

from __future__ import annotations

import logging
from typing import Literal

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from routes.agent.nodes.helpers.agui_helpers import emit_state

from core.grpc_client import file_service_client, CitationItem
from routes.agent.state import AgentState
from core.config import settings

logger = logging.getLogger(__name__)


def _format_citations(citations: list[CitationItem]) -> str:
    """Format citations as markdown with section image links."""
    if not citations:
        return ""
    lines = ["\n\n---\n**Sources:**"]
    for i, cit in enumerate(citations, 1):
        line = f"\n{i}. **{cit.node_title}** (p.{cit.page + 1})"
        if cit.section_url:
            line += f" — [View section]({cit.section_url})"
        if cit.content_preview:
            line += f"\n   > {cit.content_preview[:200]}"
        lines.append(line)
    return "\n".join(lines)


def _format_knowledge_chunks(chunks) -> tuple[str, str]:
    """Format knowledge search results as answer context + citations markdown."""
    if not chunks:
        return "", ""

    context_parts = []
    citation_lines = ["\n\n---\n**Knowledge Sources:**"]

    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[{chunk.node_title}]\n{chunk.text}")
        score_pct = int(chunk.score * 100)
        line = f"\n{i}. **{chunk.node_title}** — relevance {score_pct}% (p.{chunk.page + 1})"
        if chunk.section_url:
            line += f" — [View section]({chunk.section_url})"
        citation_lines.append(line)

    context = "\n\n".join(context_parts)
    citations = "\n".join(citation_lines)
    return context, citations


def _latest_user_question(state: AgentState) -> str:
    """Extract the most recent user message text."""
    for msg in reversed(state.get("messages", [])):
        if (
            hasattr(msg, "content")
            and isinstance(msg.content, str)
            and msg.content.strip()
            and not getattr(msg, "tool_calls", None)
        ):
            return msg.content
    return ""


# ── Node 1: document_node ─────────────────────────────────────────────

async def document_node(
    state: AgentState,
    config: RunnableConfig,
) -> Command[Literal["knowledge_node"]]:
    """
    PageIndex reasoning retrieval for user-uploaded documents.

    This node is reached after the user approves via interrupt_before.
    Iterates over uploaded_doc_ids, calls file-service gRPC for each,
    appends AI messages with answers + citations, then routes to knowledge_node.
    """
    uploaded_doc_ids = state.get("uploaded_doc_ids", [])
    if not uploaded_doc_ids:
        return Command(goto="knowledge_node", update={})

    question = _latest_user_question(state)
    if not question:
        return Command(goto="knowledge_node", update={})

    doc_messages = []
    logs = list(state.get("logs", []))

    for doc_id in uploaded_doc_ids:
        logs.append({"message": f"Searching document {doc_id[:8]}…", "done": False})
        log_idx = len(logs) - 1
        await emit_state(config, {**state, "logs": logs})

        try:
            result = await file_service_client.retrieve(doc_id, question)
            citations_md = _format_citations(result.citations)
            content = f"{result.answer}{citations_md}"
        except Exception as e:
            logger.exception("ChatSessionDocument failed for doc_id=%s", doc_id)
            content = f"[Error retrieving document {doc_id}: {e}]"

        logs[log_idx]["done"] = True
        await emit_state(config, {**state, "logs": logs})
        doc_messages.append(AIMessage(content=content))

    return Command(
        goto="knowledge_node",
        update={"messages": doc_messages, "logs": logs} if doc_messages else {"logs": logs},
    )


# ── Node 2: knowledge_node ─────────────────────────────────────────────

async def knowledge_node(
    state: AgentState,
    config: RunnableConfig,
) -> Command[Literal["search_node", "chat_node"]]:
    """
    Milvus knowledge search — triggered when research_mode=True.

    This node is reached after the user approves via interrupt_before.
    Searches across all user documents and returns ranked chunks with citations.
    """
    if not state.get("research_mode", False):
        return Command(goto="chat_node", update={})

    question = _latest_user_question(state)
    if not question:
        return Command(goto="chat_node", update={})

    mem0_user_id = state.get("mem0_user_id", "")
    logs = list(state.get("logs", []))

    logs.append({"message": "Searching knowledge base (Milvus)…", "done": False})
    log_idx = len(logs) - 1
    await emit_state(config, {**state, "logs": logs})

    try:
        chunks = await file_service_client.knowledge_search(
            user_id=mem0_user_id,
            query=question,
            top_k=settings.knowledge_top_k,
        )
        context, citations_md = _format_knowledge_chunks(chunks)
        content = (
            f"**Knowledge base results:**\n\n{context}{citations_md}"
            if chunks
            else "[No relevant knowledge found]"
        )
    except Exception as e:
        logger.exception("Knowledge search failed")
        content = f"[Knowledge search error: {e}]"

    logs[log_idx]["done"] = True
    await emit_state(config, {**state, "logs": logs})

    return Command(
        goto="search_node" if state.get("research_mode") else "chat_node",
        update={"messages": [AIMessage(content=content)], "logs": logs},
    )
