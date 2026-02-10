"""Chat Node"""

from typing import List, Literal, cast

from copilotkit.langgraph import copilotkit_customize_config
from langchain.tools import tool
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from backend.routes.agent.nodes.download import get_resource
from backend.routes.agent.nodes.model import get_model
from backend.routes.agent.state import AgentState


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


async def chat_node(
    state: AgentState, 
    config: RunnableConfig,
    mcp_tools: list = None
) -> Command[Literal["search_node", "chat_node", "delete_node", "mcp_tools", "__end__"]]:
    """
    Chat Node - handles conversation and tool routing.
    Now includes MCP tools for extended functionality.
    """

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
    
    response = await model.bind_tools(
        all_tools,
        **ainvoke_kwargs,
    ).ainvoke(
        [
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
            {resources}
            """
            ),
            *state["messages"],
        ],
        config,
    )

    ai_message = cast(AIMessage, response)

    if ai_message.tool_calls:
        if ai_message.tool_calls[0]["name"] == "WriteReport":
            report = ai_message.tool_calls[0]["args"].get("report", "")
            return Command(
                goto="chat_node",
                update={
                    "report": report,
                    "messages": [
                        ai_message,
                        ToolMessage(
                            tool_call_id=ai_message.tool_calls[0]["id"],
                            content="Report written.",
                        ),
                    ],
                },
            )
        if ai_message.tool_calls[0]["name"] == "WriteResearchQuestion":
            return Command(
                goto="chat_node",
                update={
                    "research_question": ai_message.tool_calls[0]["args"][
                        "research_question"
                    ],
                    "messages": [
                        ai_message,
                        ToolMessage(
                            tool_call_id=ai_message.tool_calls[0]["id"],
                            content="Research question written.",
                        ),
                    ],
                },
            )

    goto = "__end__"
    if ai_message.tool_calls:
        tool_name = ai_message.tool_calls[0]["name"]
        if tool_name == "Search":
            goto = "search_node"
        elif tool_name == "DeleteResources":
            goto = "delete_node"
        elif tool_name not in ["WriteReport", "WriteResearchQuestion"]:
            goto = "mcp_tools"

    return Command(goto=goto, update={"messages": response})
