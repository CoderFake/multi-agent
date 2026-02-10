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

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 60.0  # seconds
BACKOFF_MULTIPLIER = 2.0


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
    
    Args:
        model: The language model to invoke
        tools: List of tools to bind
        messages: Messages to send
        config: Runnable configuration
        ainvoke_kwargs: Additional kwargs for ainvoke
        
    Returns:
        AIMessage response from the model
        
    Raises:
        RateLimitError: If all retries are exhausted
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
                # For token limit errors, don't retry - it won't help
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
            # For other errors, don't retry
            logger.error("Unexpected error during model invocation: %s", str(e))
            raise
    
    # Should not reach here, but just in case
    raise last_error


async def chat_node(
    state: AgentState, 
    config: RunnableConfig,
    mcp_tools: list = None
) -> Command[Literal["search_node", "chat_node", "delete_node", "mcp_tools", "__end__"]]:
    """
    Chat Node - handles conversation and tool routing.
    Now includes MCP tools for extended functionality.
    """

    # Emit thinking state - shows loading spinner in chat via useCoAgentStateRender
    # IMPORTANT: emit FULL state (including resources, report, etc.) to avoid data loss
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
    
    # Truncate resources if too large to prevent token limit errors
    truncated_resources = _truncate_resources(resources, max_chars=15000)
    
    messages = [
        SystemMessage(
            content=f"""
        You are a research assistant. You help the user with writing a research report.
        
        IMPORTANT WORKFLOW:
        1. ALWAYS use the Search tool FIRST to gather information before doing anything else
        2. After gathering resources, write the research report using WriteReport tool
        3. ONLY AFTER completing the research and having sufficient data, you may use additional tools
        
        Do not recite the resources, instead use them to answer the user's question.
        If you finished writing the report, ask the user proactively for next steps, changes etc, make it engaging.
        To write the report, you should use the WriteReport tool. Never EVER respond with the report, only use the tool.
        If a research question is provided, YOU MUST NOT ASK FOR IT AGAIN.
        
        CRITICAL: If the search returns no results or insufficient information, ASK the user for clarification or more specific details instead of trying to generate a report with incomplete data.
        
        Additional tools available (use ONLY when you have sufficient data from research):
        - File system operations (read, write, list files)
        - Chart generation (requires data from research)
        - Web search capabilities
        - And other specialized tools
        
        CRITICAL: Do NOT use chart generation or other data-dependent tools until you have gathered the necessary data through Search.

        CRITICAL: RESPONSE TO USER WITH QUERY LANGUAGE 

        This is the research question:
        {research_question}

        This is the research report:
        {report}

        Here are the resources that you have available:
        {truncated_resources}
        """
        ),
        *state["messages"],
    ]
    
    response = await _invoke_with_retry(
        model=model,
        tools=all_tools,
        messages=messages,
        config=config,
        ainvoke_kwargs=ainvoke_kwargs,
    )

    # Mark thinking as done
    state["logs"][-1]["done"] = True
    await copilotkit_emit_state(config, state)

    ai_message = cast(AIMessage, response)

    if ai_message.tool_calls:
        tool_name = ai_message.tool_calls[0]["name"]
        
        # Emit tool-specific loading state
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
            # Clear logs before returning
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
            # Clear logs before returning
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
