"""Chat Node"""

import asyncio
import logging
from typing import List, Literal, cast

from copilotkit.langgraph import copilotkit_customize_config, copilotkit_emit_state
from langchain.tools import tool
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from openai import RateLimitError

from routes.agent.nodes.download import get_resource
from routes.agent.nodes.model import get_model
from routes.agent.state import AgentState
from core.config import settings
from utils.prompt_loader import render_prompt

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 60.0  # seconds
BACKOFF_MULTIPLIER = 2.0

# Lazy import memory service
_memory_service = None


def _get_memory_service():
    """Lazy import to avoid circular imports and heavy init at module load."""
    global _memory_service
    if _memory_service is None and settings.mem0_enabled:
        try:
            from services.memory_service import memory_service
            _memory_service = memory_service
        except Exception as e:
            logger.warning("Failed to load memory service: %s", e)
    return _memory_service


@tool
def Search(queries: List[str]):  # pylint: disable=invalid-name,unused-argument
    """A list of one or more search queries to find good resources to support the research."""


@tool
def WriteReport(report: str):  # pylint: disable=invalid-name,unused-argument
    """Write the research report."""


@tool
def WriteResearchQuestion(research_question: str):  # pylint: disable=invalid-name,unused-argument
    """Write the research question."""


@tool
def DeleteResources(urls: List[str]):  # pylint: disable=invalid-name,unused-argument
    """Delete the URLs from the resources."""


def _truncate_resources(resources: List[dict], max_chars: int = 15000) -> List[dict]:
    """
    Truncate resource content to prevent exceeding token limits.
    
    Args:
        resources: List of resource dictionaries with content
        max_chars: Maximum total characters for all resources
        
    Returns:
        List of resources with potentially truncated content
    """
    if not resources:
        return resources
    
    total_chars = sum(len(r.get("content", "")) for r in resources)
    
    if total_chars <= max_chars:
        return resources
    
    # Calculate per-resource limit
    chars_per_resource = max_chars // len(resources)
    truncated = []
    
    for resource in resources:
        content = resource.get("content", "")
        if len(content) > chars_per_resource:
            truncated_content = content[:chars_per_resource] + "\n... [content truncated due to length]"
            truncated.append({**resource, "content": truncated_content})
            logger.warning(
                "Truncated resource content from %d to %d chars: %s",
                len(content), chars_per_resource, resource.get("url", "unknown")
            )
        else:
            truncated.append(resource)
    
    return truncated


async def _invoke_with_retry(
    model,
    tools: list,
    messages: list,
    config: RunnableConfig,
    ainvoke_kwargs: dict,
) -> AIMessage:
    """
    Invoke model with exponential backoff retry for rate limit errors.
    """
    backoff = INITIAL_BACKOFF
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            response = await model.bind_tools(
                tools,
                **ainvoke_kwargs,
            ).ainvoke(messages, config)
            
            if attempt > 0:
                logger.info("Request succeeded after %d retries", attempt)
            
            return response
            
        except RateLimitError as e:
            last_error = e
            error_msg = str(e)
            
            # Check if it's a token limit error (request too large)
            if "tokens" in error_msg.lower() and "requested" in error_msg.lower():
                logger.error(
                    "Token limit exceeded - request is too large. "
                    "Consider reducing context or message history. Error: %s",
                    error_msg
                )
                raise
            
            # For TPM/RPM rate limits, retry with backoff
            if attempt < MAX_RETRIES - 1:
                logger.warning(
                    "Rate limit hit (attempt %d/%d). Retrying in %.1f seconds. Error: %s",
                    attempt + 1, MAX_RETRIES, backoff, error_msg
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF)
            else:
                logger.error(
                    "Rate limit exceeded after %d retries. Error: %s",
                    MAX_RETRIES, error_msg
                )
                raise
                
        except Exception as e:
            logger.error("Unexpected error during model invocation: %s", str(e))
            raise
    
    raise last_error


async def _search_user_memories(user_message: str, user_id: str) -> str:
    """Search mem0 for relevant memories with a timeout to avoid blocking chat."""
    mem_svc = _get_memory_service()
    if not mem_svc:
        return ""

    try:
        memories = await asyncio.wait_for(
            mem_svc.search_memories(query=user_message, user_id=user_id, limit=3),
            timeout=3.0,
        )
        if not memories:
            return ""

        lines = []
        for m in memories:
            memory_text = m.get("memory", "") if isinstance(m, dict) else str(m)
            if memory_text:
                lines.append(f"- {memory_text}")

        if lines:
            return "User Memories (from previous conversations):\n" + "\n".join(lines)
    except asyncio.TimeoutError:
        logger.warning("Memory search timed out (3s), skipping")
    except Exception as e:
        logger.warning("Error searching memories: %s", e)

    return ""


async def _store_conversation_memory(
    user_message: str, ai_response: str, user_id: str
):
    """Store user+assistant exchange in mem0 (fire-and-forget)."""
    mem_svc = _get_memory_service()
    if not mem_svc:
        return

    try:
        interaction = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ai_response},
        ]
        await mem_svc.add_memory(interaction, user_id=user_id)
    except Exception as e:
        logger.warning("Error storing memory: %s", e)


async def chat_node(
    state: AgentState, 
    config: RunnableConfig,
    mcp_tools: list = None
) -> Command[Literal["search_node", "chat_node", "delete_node", "mcp_tools", "__end__"]]:
    """
    Chat Node - handles conversation and tool routing.
    Now includes MCP tools and Mem0 memory integration.
    """

    # Emit thinking state
    state["logs"] = state.get("logs", [])
    state["logs"].append({"message": "Processing your request...", "done": False})
    await copilotkit_emit_state(config, state)

    config = copilotkit_customize_config(
        config,
        emit_intermediate_state=[
            {
                "state_key": "report",
                "tool": "WriteReport",
                "tool_argument": "report",
            },
            {
                "state_key": "research_question",
                "tool": "WriteResearchQuestion",
                "tool_argument": "research_question",
            },
        ],
    )

    state["resources"] = state.get("resources", [])
    research_question = state.get("research_question", "")
    report = state.get("report", "")

    # --- Extract last user message early (needed for memory search) ---
    user_id = state.get("mem0_user_id")
    last_user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if hasattr(msg, "type") and msg.type == "human":
            last_user_msg = msg.content
            break
        elif isinstance(msg, dict) and msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    # --- Start memory search in parallel with resource processing ---
    memory_task = None
    if last_user_msg and settings.mem0_enabled and user_id:
        memory_task = asyncio.create_task(
            _search_user_memories(last_user_msg, user_id)
        )

    resources = []

    for resource in state["resources"]:
        content = get_resource(resource["url"])
        if content == "ERROR":
            continue
        resources.append({**resource, "content": content})

    model = get_model(state)
    ainvoke_kwargs = {}
    if model.__class__.__name__ in ["ChatOpenAI"]:
        ainvoke_kwargs["parallel_tool_calls"] = False
    all_tools = [
        Search,
        WriteReport,
        WriteResearchQuestion,
        DeleteResources,
    ]
    
    has_resources = len(resources) > 0
    has_report = report and len(report.strip()) > 0
    
    if mcp_tools and (has_resources or has_report):
        all_tools.extend(mcp_tools)
    
    # Truncate resources if too large
    truncated_resources = _truncate_resources(resources, max_chars=15000)

    # --- Mem0: await memory search result (was started earlier in parallel) ---
    if not user_id:
        logger.warning("No mem0_user_id in state — skipping memory operations")

    memories_context = ""
    if memory_task:
        memories_context = await memory_task
        if memories_context:
            logger.info("Injected %d chars of memory context", len(memories_context))

    instructions_section = ""
    if memories_context:
        instructions_section = render_prompt(
            "memory_instructions",
            memories=memories_context,
        )

    research_context_parts = []
    if research_question:
        research_context_parts.append(f"Research question: {research_question}")
    if report:
        research_context_parts.append(f"Current report: {report}")
    if truncated_resources:
        research_context_parts.append(f"Available resources: {truncated_resources}")
    research_context = "\n".join(research_context_parts)

    research_mode = state.get("research_mode", False)
    if research_mode:
        research_mode_instruction = (
            "Research mode is ENABLED. You MUST use the Search tool to find up-to-date information "
            "from the web BEFORE answering ANY question. Always search first, then synthesize the results."
        )
    else:
        research_mode_instruction = (
            "Only activate when the user explicitly asks for research, a report, or deep investigation. "
            "Do NOT search if the user is just chatting."
        )

    system_content = render_prompt(
        "system",
        instructions_section=instructions_section,
        research_context=research_context,
        research_mode_instruction=research_mode_instruction,
    )

    messages = [
        SystemMessage(content=system_content),
        *state["messages"],
    ]

    
    response = await _invoke_with_retry(
        model=model,
        tools=all_tools,
        messages=messages,
        config=config,
        ainvoke_kwargs=ainvoke_kwargs,
    )

    state["logs"] = []
    await copilotkit_emit_state(config, state)

    ai_message = cast(AIMessage, response)

    # --- Mem0: Store conversation in memory (fire-and-forget) ---
    if settings.mem0_enabled and last_user_msg and len(last_user_msg.strip()) > 10:
        ai_content = ai_message.content or ""
        if not ai_content and ai_message.tool_calls:
            tool_info = ai_message.tool_calls[0]
            tool_args = tool_info.get("args", {})
            if tool_info["name"] == "WriteReport":
                ai_content = tool_args.get("report", "")[:500]
            elif tool_info["name"] == "WriteResearchQuestion":
                ai_content = f"Research question: {tool_args.get('research_question', '')}"
            else:
                ai_content = f"Used tool: {tool_info['name']}"

        if ai_content:
            asyncio.create_task(
                _store_conversation_memory(last_user_msg, ai_content, user_id)
            )

    if ai_message.tool_calls:
        tool_name = ai_message.tool_calls[0]["name"]
        
        if tool_name == "Search":
            state["logs"].append({"message": "Preparing to search...", "done": False})
        elif tool_name == "WriteReport":
            state["logs"].append({"message": "Writing research report...", "done": False})
        elif tool_name == "WriteResearchQuestion":
            state["logs"].append({"message": "Setting research question...", "done": False})
        elif tool_name == "DeleteResources":
            state["logs"].append({"message": "Preparing resource deletion...", "done": False})
        else:
            state["logs"].append({"message": f"Executing {tool_name}...", "done": False})
        await copilotkit_emit_state(config, state)

        if tool_name == "WriteReport":
            report = ai_message.tool_calls[0]["args"].get("report", "")
            state["logs"] = []
            await copilotkit_emit_state(config, state)
            return Command(
                goto="chat_node",
                update={
                    "report": report,
                    "logs": [],
                    "messages": [
                        ai_message,
                        ToolMessage(
                            tool_call_id=ai_message.tool_calls[0]["id"],
                            content="Report written.",
                        ),
                    ],
                },
            )
        if tool_name == "WriteResearchQuestion":
            state["logs"] = []
            await copilotkit_emit_state(config, state)
            return Command(
                goto="chat_node",
                update={
                    "research_question": ai_message.tool_calls[0]["args"][
                        "research_question"
                    ],
                    "logs": [],
                    "messages": [
                        ai_message,
                        ToolMessage(
                            tool_call_id=ai_message.tool_calls[0]["id"],
                            content="Research question written.",
                        ),
                    ],
                },
            )

    # Clear logs before final routing
    state["logs"] = []
    await copilotkit_emit_state(config, state)

    goto = "__end__"
    if ai_message.tool_calls:
        tool_name = ai_message.tool_calls[0]["name"]
        if tool_name == "Search":
            goto = "search_node"
        elif tool_name == "DeleteResources":
            goto = "delete_node"
        elif tool_name not in ["WriteReport", "WriteResearchQuestion"]:
            goto = "mcp_tools"

    return Command(goto=goto, update={"messages": response, "logs": []})


