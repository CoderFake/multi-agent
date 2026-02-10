"""
MCP Tools Execution Node
Simple logs emission following research-canvas download.py pattern exactly
"""

import logging
from typing import Literal
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from copilotkit.langgraph import copilotkit_emit_state
from routes.agent.state import AgentState

logger = logging.getLogger(__name__)


async def mcp_tools_node(
    state: AgentState,
    config: RunnableConfig,
    mcp_manager,
    tool_to_mcp_id: dict
) -> Command[Literal["chat_node"]]:
    """
    Execute MCP tools with logs emission.
    Follows research-canvas download_node pattern EXACTLY.
    """
    messages = state.get("messages", [])
    if not messages:
        return Command(goto="chat_node", update={})
    
    last_message = messages[-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return Command(goto="chat_node", update={})
    
    # Initialize logs (like research-canvas)
    state["logs"] = state.get("logs", [])
    
    valid_mcp_calls = []
    invalid_calls = []
    
    # 1. Separate valid commands from invalid ones
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        if tool_name in tool_to_mcp_id:
            valid_mcp_calls.append(tool_call)
            state["logs"].append({
                "message": f"Executing {tool_name}...",
                "done": False
            })
        else:
            invalid_calls.append(tool_call)
    
    # 2. Emit state if we have valid tools to execute (show spinner)
    if valid_mcp_calls:
        await copilotkit_emit_state(config, state)
    
    tool_messages = []
    log_index = len(state["logs"]) - len(valid_mcp_calls)
    
    # 3. Execute valid MCP tools
    for i, tool_call in enumerate(valid_mcp_calls):
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]
        
        mcp_id = tool_to_mcp_id[tool_name]
        
        try:
            # Execute MCP tool
            result_dict = await mcp_manager.invoke_tool(
                mcp_id=mcp_id,
                tool_name=tool_name,
                arguments=tool_args
            )
            
            if not result_dict.get("success"):
                result_text = f"Error: {result_dict.get('error', 'Unknown error')}"
            else:
                # Extract text from result
                result = result_dict.get("result", [])
                if isinstance(result, list):
                    texts = [
                        item.get("text", str(item)) if isinstance(item, dict) else str(item)
                        for item in result
                    ]
                    result_text = "\n".join(texts) if texts else "Success"
                elif isinstance(result, dict):
                    result_text = result.get("text", str(result))
                else:
                    result_text = str(result) if result else "Success"
                    
        except Exception as e:
            logger.exception(f"Error executing {tool_name}")
            result_text = f"Error: {str(e)}"
        
        # Create tool message
        tool_messages.append(ToolMessage(
            content=result_text,
            tool_call_id=tool_id
        ))
        
        # Mark this log as done
        state["logs"][log_index + i]["done"] = True
        
        # Emit state after each tool
        await copilotkit_emit_state(config, state)
        
    # 4. Handle invalid/unknown tools (Return error messages)
    for tool_call in invalid_calls:
        tool_messages.append(ToolMessage(
            content=f"Tool '{tool_call['name']}' is not available as an MCP tool.",
            tool_call_id=tool_call["id"]
        ))
    
    # Route back to chat
    return Command(goto="chat_node", update={"messages": tool_messages})
