"""
Agent Graph - Research-canvas pattern + MCP tools
Combines research features (search, download, delete) with MCP tool execution
"""

import os
import logging
import asyncio
from functools import partial
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model
from typing import Any, Dict, List, Optional
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

from services.mcp_manager import mcp_manager
from routes.agent.state import AgentState
from routes.agent.nodes.chat import chat_node
from routes.agent.nodes.search import search_node
from routes.agent.nodes.download import download_node
from routes.agent.nodes.delete import delete_node, perform_delete_node
from routes.agent.nodes.mcp_tools import mcp_tools_node
from routes.agent.nodes.model import get_model

logger = logging.getLogger(__name__)


def _create_mcp_tool_wrapper(mcp_id: str, tool_name: str, tool_config: dict):
    """
    Create a LangChain StructuredTool from MCP tool config.
    Uses StructuredTool.from_function to avoid Pydantic recursion issues.
    """
    input_schema = tool_config.get("inputSchema", {})
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])
    
    if not properties:
        async def tool_func():
            """Execute MCP tool with no arguments"""
            result_dict = await mcp_manager.invoke_tool(mcp_id, tool_name, {})
            return result_dict.get("result", "Success")
        
        return StructuredTool.from_function(
            coroutine=tool_func,
            name=tool_name,
            description=tool_config.get("description", "")
        )
    
    fields = {}
    for prop_name, prop_schema in properties.items():
        field_type = Any
        field_description = prop_schema.get("description", "")
        
        json_type = prop_schema.get("type")
        
        if json_type == "string":
            field_type = str
        elif json_type == "number":
            field_type = float
        elif json_type == "integer":
            field_type = int
        elif json_type == "boolean":
            field_type = bool
        elif json_type == "array":
            items_schema = prop_schema.get("items", {})
            items_type = items_schema.get("type")
            
            if items_type == "object":
                field_type = List[Dict[str, Any]]
            elif items_type == "string":
                field_type = List[str]
            elif items_type == "number":
                field_type = List[float]
            elif items_type == "integer":
                field_type = List[int]
            else:
                field_type = List[Any]
        elif json_type == "object":
            field_type = Dict[str, Any]
        
        if prop_name in required:
            fields[prop_name] = (field_type, Field(description=field_description))
        else:
            fields[prop_name] = (field_type, Field(default=None, description=field_description))
    
    InputModel = create_model(f"{tool_name}Input", **fields)
    
    async def tool_func(**kwargs):
        """Execute MCP tool with arguments"""
        result_dict = await mcp_manager.invoke_tool(mcp_id, tool_name, kwargs)
        return result_dict.get("result", "Success")
    
    return StructuredTool.from_function(
        coroutine=tool_func,
        name=tool_name,
        description=tool_config.get("description", ""),
        args_schema=InputModel
    )


async def _load_mcp_tools():
    """Load MCP tools and create LangChain StructuredTool wrappers"""
    all_tools = []
    tool_to_mcp_id = {}
    
    try:
        mcps = await mcp_manager.list_mcps()
        logger.info(f"Found {len(mcps)} MCP servers")
        
        for mcp in mcps:
            for tool_config in mcp.tools:
                tool_name = tool_config.get("name")
                tool_to_mcp_id[tool_name] = mcp.id
                
                tool = _create_mcp_tool_wrapper(mcp.id, tool_name, tool_config)
                all_tools.append(tool)
        
        logger.info(f"Loaded {len(all_tools)} MCP tools")
        return all_tools, tool_to_mcp_id
    
    except Exception as e:
        logger.exception("Error loading MCP tools")
        return [], {}


async def create_agent_graph():
    """
    Create agent graph combining research-canvas + MCP tools.
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