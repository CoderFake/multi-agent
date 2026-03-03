"""
Document MCP Tools Node — ChatSessionDocument + Knowledge

Two HITL-gated tools integrated as LangGraph nodes:

  1. ChatSessionDocument:
     – PageIndex reasoning over a specific document the user uploaded
     – Returns answer + per-section citations (table/figure/formula)

  2. Knowledge:
     – Milvus semantic search across all user's indexed knowledge base
     – Returns relevant chunks + citations with section images

Both tools follow the same HITL pattern as mcp_tools_node:
  interrupt() → user Approve/Reject → execute → Command(goto=next_node)
"""

from __future__ import annotations

import json
import logging
from typing import Literal

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt
from copilotkit.langgraph import copilotkit_emit_state

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


# ── Node 1: document_node ─────────────────────────────────────────────

async def document_node(
    state: AgentState,
    config: RunnableConfig,
) -> Command[Literal["knowledge_node", "chat_node"]]:
    """
    PageIndex reasoning retrieval for user-uploaded documents.
    Triggers for each doc_id in state.uploaded_doc_ids.
    HITL: user approves before gRPC call.
    """
    uploaded_doc_ids = state.get("uploaded_doc_ids", [])
    if not uploaded_doc_ids:
        return Command(goto="knowledge_node", update={})

    messages = state.get("messages", [])
    # Find the latest user question
    question = ""
    for msg in reversed(messages):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            if not hasattr(msg, "tool_calls"):
                question = msg.content
                break
    if not question:
        return Command(goto="knowledge_node", update={})

    mem0_user_id = state.get("mem0_user_id", "")
    doc_messages = []

    for doc_id in uploaded_doc_ids:
        # ── HITL: ask approval ────────────────────────────────────────
        decision = interrupt({
            "type": "approval",
            "tool_name": "ChatSessionDocument",
            "args": {"doc_id": doc_id, "question": question[:200]},
            "args_preview": json.dumps({"doc_id": doc_id, "question": question[:200]}),
        })

        if str(decision).lower() in ("rejected", "false", "no", "deny"):
            logger.info("User rejected ChatSessionDocument for doc_id=%s", doc_id)
            doc_messages.append(AIMessage(
                content=f"[Document retrieval for {doc_id} skipped by user]"
            ))
            continue

        # ── Execute: gRPC PageIndex retrieval ─────────────────────────
        state.setdefault("logs", []).append({
            "message": f"Searching document {doc_id[:8]}…",
            "done": False,
        })
        log_idx = len(state["logs"]) - 1
        await copilotkit_emit_state(config, state)

        try:
            result = await file_service_client.retrieve(doc_id, question)
            citations_md = _format_citations(result.citations)
            content = f"{result.answer}{citations_md}"
        except Exception as e:
            logger.exception("ChatSessionDocument failed for doc_id=%s", doc_id)
            content = f"[Error retrieving document {doc_id}: {e}]"

        state["logs"][log_idx]["done"] = True
        await copilotkit_emit_state(config, state)

        doc_messages.append(AIMessage(content=content))

    # Route to knowledge_node next (will also check research_mode)
    return Command(
        goto="knowledge_node",
        update={"messages": doc_messages} if doc_messages else {},
    )


# ── Node 2: knowledge_node ─────────────────────────────────────────────

async def knowledge_node(
    state: AgentState,
    config: RunnableConfig,
) -> Command[Literal["chat_node"]]:
    """
    Milvus knowledge search — triggered when research_mode=True.
    Searches across all user documents and returns ranked chunks with citations.
    HITL: user approves before gRPC search.
    """
    if not state.get("research_mode", False):
        return Command(goto="chat_node", update={})

    messages = state.get("messages", [])
    question = ""
    for msg in reversed(messages):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            if not hasattr(msg, "tool_calls"):
                question = msg.content
                break
    if not question:
        return Command(goto="chat_node", update={})

    mem0_user_id = state.get("mem0_user_id", "")

    # ── HITL: ask approval ────────────────────────────────────────────
    decision = interrupt({
        "type": "approval",
        "tool_name": "Knowledge",
        "args": {"query": question[:200]},
        "args_preview": json.dumps({"query": question[:200], "mode": "knowledge_base_search"}),
    })

    if str(decision).lower() in ("rejected", "false", "no", "deny"):
        logger.info("User rejected Knowledge search")
        return Command(goto="chat_node", update={})

    # ── Execute: Milvus knowledge search ─────────────────────────────
    state.setdefault("logs", []).append({
        "message": "Searching knowledge base (Milvus)…",
        "done": False,
    })
    log_idx = len(state["logs"]) - 1
    await copilotkit_emit_state(config, state)

    try:
        chunks = await file_service_client.knowledge_search(
            user_id=mem0_user_id,
            query=question,
            top_k=settings.knowledge_top_k,
        )
        context, citations_md = _format_knowledge_chunks(chunks)
        content = f"**Knowledge base results:**\n\n{context}{citations_md}" if chunks else "[No relevant knowledge found]"
    except Exception as e:
        logger.exception("Knowledge search failed")
        content = f"[Knowledge search error: {e}]"

    state["logs"][log_idx]["done"] = True
    await copilotkit_emit_state(config, state)

    return Command(
        goto="chat_node",
        update={"messages": [AIMessage(content=content)]},
    )
