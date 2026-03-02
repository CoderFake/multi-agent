"""
Agent Graph - Research-canvas pattern + MCP tools
Uses langchain-mcp-adapters for correct tool schema handling (no type transformation)
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
from routes.agent.nodes.mcp_tools import mcp_tools_node

logger = logging.getLogger(__name__)


def _build_mcp_connections(mcps) -> Dict[str, Any]:
    """
    Build connection dict for MultiServerMCPClient from persisted MCP configs.
    langchain-mcp-adapters handles tool.inputSchema directly — no type transformation.
    """
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
            conn = {
                "transport": "sse",
                "url": cfg["url"],
            }
            if cfg.get("headers"):
                conn["headers"] = cfg["headers"]
        else:
            logger.warning(
                "Unsupported MCP protocol '%s' for server '%s', skipping",
                protocol, mcp.name
            )
            continue

        connections[mcp.name] = conn

    return connections


async def _load_mcp_tools():
    """
    Load MCP tools via langchain-mcp-adapters MultiServerMCPClient.

    Key benefit: tool.inputSchema (dict[str, Any] per MCP spec) is passed
    DIRECTLY as StructuredTool.args_schema — no manual parsing, no type loss.
    """
    all_tools: List = []
    tool_to_mcp_id: Dict[str, str] = {}

    try:
        mcps = await mcp_manager.list_mcps()
        if not mcps:
            logger.info("No MCP servers configured")
            return [], {}

        logger.info(
            "Found %d MCP servers, loading tools via langchain-mcp-adapters", len(mcps)
        )

        connections = _build_mcp_connections(mcps)
        if not connections:
            return [], {}

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
                    if mcp_id:
                        tool_to_mcp_id[tool.name] = mcp_id
            except Exception:
                logger.exception(
                    "Failed to load tools from MCP server '%s'", server_name
                )

        logger.info(
            "Loaded %d MCP tools from %d servers",
            len(all_tools), len(connections)
        )
        return all_tools, tool_to_mcp_id

    except Exception:
        logger.exception("Error loading MCP tools via langchain-mcp-adapters")
        return [], {}


async def create_agent_graph():
    """
    Create agent graph combining research-canvas + MCP tools.
    MCP tools loaded via langchain-mcp-adapters — preserves exact inputSchema types.
    """
    logger.info("Creating agent graph...")

    mcp_tools, tool_to_mcp_id = await _load_mcp_tools()

    workflow = StateGraph(AgentState)

    workflow.add_node("download", download_node)
    workflow.add_node("chat_node", partial(
        chat_node,
        mcp_tools=mcp_tools
    ))
    workflow.add_node("search_node", search_node)
    workflow.add_node("delete_node", delete_node)
    workflow.add_node("perform_delete_node", perform_delete_node)

    workflow.add_node("mcp_tools", partial(
        mcp_tools_node,
        mcp_manager=mcp_manager,
        tool_to_mcp_id=tool_to_mcp_id
    ))

    workflow.set_entry_point("download")
    workflow.add_edge("download", "chat_node")
    workflow.add_edge("delete_node", "perform_delete_node")
    workflow.add_edge("perform_delete_node", "chat_node")
    workflow.add_edge("search_node", "download")
    workflow.add_edge("mcp_tools", "chat_node")

    memory = MemorySaver()
    graph = workflow.compile(
        checkpointer=memory,
        interrupt_after=["delete_node"]
    )

    logger.info("Agent graph compiled successfully")
    return graph