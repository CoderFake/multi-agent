"""
Chat Node — handles conversation, memory injection, and routing.

Responsibilities:
  - Build system prompt (memory + research context)
  - Invoke LLM with research + MCP tools
  - Route: Search → search_node, Delete → delete_node, MCP → mcp_tools, else → plan_node
"""

import asyncio
import logging
from typing import Literal, cast

from copilotkit.langgraph import copilotkit_customize_config
from routes.agent.nodes.helpers.agui_helpers import emit_state
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from openai import RateLimitError

from routes.agent.nodes.tools.chat_tools import (
    Search, WriteReport, WriteResearchQuestion, DeleteResources,
    truncate_resources,
)
from routes.agent.nodes.helpers.memory_helpers import search_user_memories, store_conversation_memory
from routes.agent.nodes.download import get_resource
from routes.agent.nodes.helpers.model import get_model
from routes.agent.state import AgentState
from core.config import settings
from utils.prompt_loader import render_prompt

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 60.0
BACKOFF_MULTIPLIER = 2.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sanitize_messages(messages: list) -> list:
    """
    1. Deduplicate ToolMessages by tool_call_id — keeps first occurrence.
       (ag_ui replays history on every turn, causing duplicates in state.)
    2. Drop ToolMessages not immediately preceded by an AIMessage with matching tool_calls.
       (OpenAI 400: tool message must follow tool_calls.)
    """
    # Step 1: deduplicate ToolMessages by tool_call_id
    seen_call_ids: set = set()
    deduped: list = []
    for msg in messages:
        if getattr(msg, "type", None) == "tool":
            cid = getattr(msg, "tool_call_id", None)
            if cid in seen_call_ids:
                continue
            seen_call_ids.add(cid)
        deduped.append(msg)

    # Step 2: consecutive-pair check
    result: list = []
    for msg in deduped:
        if getattr(msg, "type", None) == "tool":
            call_id = getattr(msg, "tool_call_id", None)
            if not result:
                continue
            prev = result[-1]
            prev_ids = {
                (tc["id"] if isinstance(tc, dict) else tc.id)
                for tc in (getattr(prev, "tool_calls", None) or [])
            }
            if call_id not in prev_ids:
                logger.debug("Dropping orphaned ToolMessage tool_call_id=%s", call_id)
                continue
        result.append(msg)
    return result


async def _invoke_with_retry(
    model,
    tools: list,
    messages: list,
    config: RunnableConfig,
    ainvoke_kwargs: dict,
) -> AIMessage:
    """Invoke model with exponential-backoff retry on rate limit errors."""
    backoff = INITIAL_BACKOFF
    last_err = None

    for attempt in range(MAX_RETRIES):
        try:
            return await model.bind_tools(tools, **ainvoke_kwargs).ainvoke(messages, config)
        except RateLimitError as exc:
            last_err = exc
            if "tokens" in str(exc).lower() and "requested" in str(exc).lower():
                logger.error("Token limit exceeded (request too large): %s", exc)
                raise
            if attempt < MAX_RETRIES - 1:
                logger.warning("Rate limit (attempt %d/%d), retry in %.1fs", attempt + 1, MAX_RETRIES, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
            else:
                logger.error("Rate limit after %d retries: %s", MAX_RETRIES, exc)
                raise
        except Exception as exc:
            logger.error("Unexpected model error: %s", exc)
            raise

    raise last_err


# ── chat_node ─────────────────────────────────────────────────────────────────

async def chat_node(
    state: AgentState,
    config: RunnableConfig,
    mcp_tools: list = None,
) -> Command[Literal["search_node", "chat_node", "delete_node", "mcp_tools", "plan_node", "__end__"]]:
    """
    Main chat node.
    1. Fetch resources + search memories (parallel)
    2. Build system prompt
    3. Invoke LLM
    4. Handle tool routing (Write* → immediate ToolMessage + loop, else → routing)
    """
    mcp_tools = mcp_tools or []

    state["logs"] = [{"message": "Processing your request...", "done": False}]
    state["execution_plan"] = []
    await emit_state(config, state)

    config = copilotkit_customize_config(
        config,
        emit_intermediate_state=[
            {"state_key": "report", "tool": "WriteReport", "tool_argument": "report"},
            {"state_key": "research_question", "tool": "WriteResearchQuestion", "tool_argument": "research_question"},
        ],
    )

    # --- Last user message (for memory) ---
    user_id = state.get("mem0_user_id")
    last_user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if getattr(msg, "type", None) == "human":
            last_user_msg = msg.content
            break
        if isinstance(msg, dict) and msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    # --- Start memory search in parallel with resource fetch ---
    memory_task = None
    if last_user_msg and settings.mem0_enabled and user_id:
        memory_task = asyncio.create_task(search_user_memories(last_user_msg, user_id))

    # --- Fetch + truncate resources ---
    resources = []
    for r in state.get("resources", []):
        content = get_resource(r["url"])
        if content != "ERROR":
            resources.append({**r, "content": content})
    resources = truncate_resources(resources, max_chars=15000)

    # --- Model setup ---
    model = get_model(state)
    ainvoke_kwargs = {}
    if model.__class__.__name__ == "ChatOpenAI":
        ainvoke_kwargs["parallel_tool_calls"] = False

    research_question = state.get("research_question", "")
    report = state.get("report", "")

    all_tools = [Search, WriteReport, WriteResearchQuestion, DeleteResources]
    if mcp_tools and (resources or report):
        all_tools.extend(mcp_tools)

    # --- Await memory ---
    if not user_id:
        logger.warning("No mem0_user_id — skipping memory")
    memories_context = await memory_task if memory_task else ""
    if memories_context:
        logger.info("Injected %d chars of memory context", len(memories_context))

    # --- Build system prompt ---
    instructions_section = (
        render_prompt("memory_instructions", memories=memories_context)
        if memories_context else ""
    )

    research_context_parts = []
    if research_question:
        research_context_parts.append(f"Research question: {research_question}")
    if report:
        research_context_parts.append(f"Current report: {report}")
    if resources:
        research_context_parts.append(f"Available resources: {resources}")

    research_mode = state.get("research_mode", False)
    research_mode_instruction = (
        "Research mode is ENABLED. Use Search BEFORE answering ANY question."
        if research_mode
        else "Only activate search when the user explicitly requests research or a report."
    )

    system_content = render_prompt(
        "system",
        instructions_section=instructions_section,
        research_context="\n".join(research_context_parts),
        research_mode_instruction=research_mode_instruction,
    )

    messages = [SystemMessage(content=system_content), *_sanitize_messages(state["messages"])]

    # --- LLM call ---
    response = await _invoke_with_retry(
        model=model,
        tools=all_tools,
        messages=messages,
        config=config,
        ainvoke_kwargs=ainvoke_kwargs,
    )

    state["logs"] = []
    await emit_state(config, state)

    ai_message = cast(AIMessage, response)

    # --- Store memory (fire-and-forget) ---
    if settings.mem0_enabled and last_user_msg and len(last_user_msg.strip()) > 10:
        ai_content = ai_message.content or ""
        if not ai_content and ai_message.tool_calls:
            tc = ai_message.tool_calls[0]
            args = tc.get("args", {})
            if tc["name"] == "WriteReport":
                ai_content = args.get("report", "")[:500]
            elif tc["name"] == "WriteResearchQuestion":
                ai_content = f"Research question: {args.get('research_question', '')}"
            else:
                ai_content = f"Used tool: {tc['name']}"
        if ai_content:
            asyncio.create_task(store_conversation_memory(last_user_msg, ai_content, user_id))

    # --- Handle Write* tools immediately (loop back) ---
    if ai_message.tool_calls:
        tool_name = ai_message.tool_calls[0]["name"]
        tool_id = ai_message.tool_calls[0]["id"]

        if tool_name == "WriteReport":
            report_text = ai_message.tool_calls[0]["args"].get("report", "")
            state["logs"] = []
            await emit_state(config, state)
            return Command(
                goto="chat_node",
                update={
                    "report": report_text,
                    "logs": [],
                    "messages": [ai_message, ToolMessage(tool_call_id=tool_id, content="Report written.")],
                },
            )

        if tool_name == "WriteResearchQuestion":
            state["logs"] = []
            await emit_state(config, state)
            return Command(
                goto="chat_node",
                update={
                    "research_question": ai_message.tool_calls[0]["args"]["research_question"],
                    "logs": [],
                    "messages": [ai_message, ToolMessage(tool_call_id=tool_id, content="Research question set.")],
                },
            )

        # Log other tool execution
        log_label = {
            "Search": "Preparing to search...",
            "DeleteResources": "Preparing resource deletion...",
        }.get(tool_name, f"Executing {tool_name}...")
        state["logs"].append({"message": log_label, "done": False})
        await emit_state(config, state)

    state["logs"] = []
    await emit_state(config, state)

    # --- Route ---
    goto: str = "__end__"
    if ai_message.tool_calls:
        tool_name = ai_message.tool_calls[0]["name"]
        if tool_name == "Search":
            goto = "search_node"
        elif tool_name == "DeleteResources":
            goto = "delete_node"
        elif tool_name not in ("WriteReport", "WriteResearchQuestion"):
            goto = "mcp_tools"

    return Command(goto=goto, update={"messages": response, "logs": []})

