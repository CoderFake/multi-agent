"""
Agent Graph - Research-canvas pattern + MCP tools + Document Intelligence

Reasoning flow:
  START
    → download_node         (load resources from state)
    → chat_node             (mem0 context, tool binding)
    → document_node         (HITL, if uploaded_doc_ids non-empty)
    → knowledge_node        (HITL, if research_mode=True — Milvus RAG)
    → search_node           (Tavily web search, if research_mode=True)
    → mcp_tools             (HITL, external MCP tool execution)
    → chat_node             (final synthesis with all context + citations)
    → END
"""

import asyncio
import logging
from functools import partial
from typing import Any, Dict, List

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

from services.mcp_manager import mcp_manager
from routes.agent.state import AgentState
from routes.agent.nodes.chat import chat_node
from routes.agent.nodes.search import search_node
from routes.agent.nodes.download import download_node
from routes.agent.nodes.delete import delete_node, perform_delete_node
from routes.agent.nodes.tools.mcp_tools import mcp_tools_node
from routes.agent.nodes.tools.document_tools import document_node, knowledge_node
from routes.agent.nodes.plan import make_plan_node

logger = logging.getLogger(__name__)


def _build_mcp_connections(mcps) -> Dict[str, Any]:
    connections = {}
    for mcp in mcps:
        cfg = mcp.config
        protocol = mcp.protocol

        if protocol == "stdio":
            conn: Dict[str, Any] = {
                "transport": "stdio",
                "command": cfg["command"],
                "args": cfg.get("args", []),
            }
            if cfg.get("env"):
                conn["env"] = cfg["env"]
        elif protocol in ("sse", "http"):
            conn = {"transport": "sse", "url": cfg["url"]}
            if cfg.get("headers"):
                conn["headers"] = cfg["headers"]
        else:
            logger.warning("Unsupported MCP protocol '%s' for '%s', skipping", protocol, mcp.name)
            continue

        connections[mcp.name] = conn
    return connections


async def _load_mcp_tools():
    all_tools: List = []
    tool_to_mcp_id: Dict[str, str] = {}
    tool_map: Dict[str, Any] = {} 

    try:
        mcps = await mcp_manager.list_mcps()
        if not mcps:
            logger.info("No MCP servers configured")
            return [], {}, {}

        connections = _build_mcp_connections(mcps)
        if not connections:
            return [], {}, {}

        name_to_id = {mcp.name: mcp.id for mcp in mcps}
        client = MultiServerMCPClient(connections)

        per_server_tasks = {
            name: asyncio.create_task(client.get_tools(server_name=name))
            for name in connections
        }

        for server_name, task in per_server_tasks.items():
            try:
                server_tools = await task
                mcp_id = name_to_id.get(server_name)
                for tool in server_tools:
                    all_tools.append(tool)
                    tool_map[tool.name] = tool  
                    if mcp_id:
                        tool_to_mcp_id[tool.name] = mcp_id
            except Exception:
                logger.exception("Failed to load tools from MCP server '%s'", server_name)

        logger.info("Loaded %d MCP tools from %d servers", len(all_tools), len(connections))
        return all_tools, tool_to_mcp_id, tool_map

    except Exception:
        logger.exception("Error loading MCP tools")
        return [], {}, {}


# ── Conditional routing ────────────────────────────────────────────────

def _route_from_chat(state: AgentState) -> str:
    """
    After chat_node:
      - pending_approval + user said 'approved' → plan_node (resume HITL)
      - tool_calls → appropriate tool node
      - uploaded_doc_ids → document_node
      - else → __end__
    """
    messages = state.get("messages", [])
    if not messages:
        return "__end__"

    last = messages[-1]
    last_content = ""
    if hasattr(last, "content"):
        last_content = (last.content or "").strip().lower()
    elif isinstance(last, dict):
        last_content = (last.get("content") or "").strip().lower()

    if state.get("pending_approval") and state.get("execution_plan"):
        if last_content in ("approved", "yes", "approve", "ok", "confirm",
                             "rejected", "reject", "no", "deny", "cancel"):
            return "plan_node"

    if hasattr(last, "tool_calls") and last.tool_calls:
        return "mcp_tools"

    if state.get("uploaded_doc_ids"):
        return "document_node"

    return "__end__"


def _route_from_document(state: AgentState) -> str:
    """After document_node → knowledge_node (always, to check research_mode)."""
    return "knowledge_node"


def _route_from_knowledge(state: AgentState) -> str:
    """After knowledge_node → search_node if research_mode, else plan_node."""
    if state.get("research_mode", False):
        return "search_node"
    return "plan_node"


# ── Graph construction ─────────────────────────────────────────────────

async def create_agent_graph():
    """
    Create agent graph: research-canvas + MCP tools + Document Intelligence pipeline.
    """
    logger.info("Creating agent graph…")
    mcp_tools, tool_to_mcp_id, tool_map = await _load_mcp_tools()

    workflow = StateGraph(AgentState)

    # ── Nodes ────────────────────────────────────────────────────────
    workflow.add_node("download", download_node)
    workflow.add_node("chat_node", partial(chat_node, mcp_tools=mcp_tools))
    workflow.add_node("document_node", document_node)
    workflow.add_node("knowledge_node", knowledge_node)
    workflow.add_node("search_node", search_node)
    workflow.add_node("plan_node", make_plan_node(mcp_tools))
    workflow.add_node("delete_node", delete_node)
    workflow.add_node("perform_delete_node", perform_delete_node)
    workflow.add_node("mcp_tools", partial(
        mcp_tools_node,
        tool_map=tool_map,
    ))

    # ── Edges ────────────────────────────────────────────────────────
    workflow.set_entry_point("download")
    workflow.add_edge("download", "chat_node")

    # chat_node → conditional: plan resume | MCP tools | document_node | __end__
    workflow.add_conditional_edges(
        "chat_node",
        _route_from_chat,
        {
            "plan_node": "plan_node",
            "mcp_tools": "mcp_tools",
            "document_node": "document_node",
            "__end__": "__end__",
        },
    )


    # document_node → knowledge_node
    workflow.add_conditional_edges(
        "document_node",
        _route_from_document,
        {"knowledge_node": "knowledge_node"},
    )

    workflow.add_conditional_edges(
        "knowledge_node",
        _route_from_knowledge,
        {
            "search_node": "search_node",
            "plan_node": "plan_node",
        },
    )

    workflow.add_edge("search_node", "plan_node")
    workflow.add_edge("delete_node", "perform_delete_node")
    workflow.add_edge("perform_delete_node", "chat_node")
    workflow.add_edge("mcp_tools", "chat_node")

    memory = MemorySaver()
    graph = workflow.compile(
        checkpointer=memory,
        interrupt_after=["delete_node"],
    )

    logger.info("Agent graph compiled successfully")
    return graph