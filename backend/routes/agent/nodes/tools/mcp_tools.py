"""
MCP Tools Execution Node — with HITL interrupt before each tool call.

Flow per tool call:
  1. interrupt({ type: "approval", tool_name, args, description })
  2. Frontend shows Approve / Reject card
  3. resume("approved")  → execute tool via LangChain tool object (preserves exact schema)
  4. resume("rejected")  → return graceful refusal message
"""

import json
import logging
from typing import Literal
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt
from routes.agent.nodes.helpers.agui_helpers import emit_state
from routes.agent.state import AgentState

logger = logging.getLogger(__name__)


async def mcp_tools_node(
    state: AgentState,
    config: RunnableConfig,
    tool_map: dict,  # { tool_name: LangChain BaseTool }
) -> Command[Literal["chat_node"]]:
    """
    Execute MCP tools — pauses before each one for user approval (HITL).
    Uses LangChain tool objects (from langchain-mcp-adapters) for invocation,
    which preserves the exact inputSchema from the MCP server without any
    field renaming or type coercion.
    """
    messages = state.get("messages", [])
    if not messages:
        return Command(goto="chat_node", update={})

    last_message = messages[-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return Command(goto="chat_node", update={})

    state["logs"] = state.get("logs", [])

    valid_calls = []
    invalid_calls = []

    for tool_call in last_message.tool_calls:
        if tool_call["name"] in tool_map:
            valid_calls.append(tool_call)
        else:
            invalid_calls.append(tool_call)

    tool_messages = []

    # ── HITL + execution for each MCP tool ─────────────────────────────
    for tool_call in valid_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]
        tool_obj = tool_map[tool_name]

        # Build a human-readable args summary (truncate if huge)
        try:
            args_str = json.dumps(tool_args, ensure_ascii=False)
            if len(args_str) > 300:
                args_str = args_str[:297] + "…"
        except Exception:
            args_str = str(tool_args)

        # ── HITL: pause and ask user ────────────────────────────────────
        decision = interrupt({
            "type": "approval",
            "tool_name": tool_name,
            "args": tool_args,
            "args_preview": args_str,
        })

        if str(decision).lower() in ("rejected", "false", "no", "deny"):
            logger.info("User rejected tool call: %s", tool_name)
            tool_messages.append(ToolMessage(
                content=f"User rejected the action '{tool_name}'. Skipping.",
                tool_call_id=tool_id,
            ))
            continue

        # ── Execute approved tool via LangChain (preserves schema) ──────
        state["logs"].append({"message": f"Executing {tool_name}…", "done": False})
        log_idx = len(state["logs"]) - 1
        await emit_state(config, state)

        try:
            result = await tool_obj.ainvoke(tool_args, config)
            if isinstance(result, str):
                result_text = result
            elif isinstance(result, list):
                result_text = "\n".join(
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in result
                ) or "Success"
            elif isinstance(result, dict):
                result_text = result.get("text", str(result))
            else:
                result_text = str(result) if result is not None else "Success"

        except Exception as e:
            logger.exception("Error executing %s", tool_name)
            result_text = f"Error: {e}"

        tool_messages.append(ToolMessage(content=result_text, tool_call_id=tool_id))
        state["logs"][log_idx]["done"] = True
        await emit_state(config, state)

    # ── Unknown / non-MCP tools ─────────────────────────────────────────
    for tool_call in invalid_calls:
        tool_messages.append(ToolMessage(
            content=f"Tool '{tool_call['name']}' is not available as an MCP tool.",
            tool_call_id=tool_call["id"],
        ))

    return Command(goto="chat_node", update={"messages": tool_messages})
