"""Web search agent definition.

This agent handles web search queries using Google Search grounding.
It is wrapped as an AgentTool for use by the root agent.

Note: google_search has a single-tool-per-agent constraint.
The AgentTool pattern allows it to coexist with other tools in the root agent.

The capture_grounding_metadata callback captures Google Search's grounding
metadata (sources, citations) and embeds it in the response for frontend
rendering.
"""

from google.adk.agents import LlmAgent
from google.adk.planners import BuiltInPlanner
from google.adk.tools import google_search
from google.genai.types import ThinkingConfig

from callbacks import capture_grounding_metadata
from config.settings import settings
from instructions import search_instruction
from agents.mcp_manager import get_mcp_tools


search_mcp_tools = get_mcp_tools("search")

search_agent = LlmAgent(
    name="web_search",
    model=settings.MODEL_SEARCH,
    description="Searches the web for current information, news, and facts.",
    tools=[google_search],
    after_model_callback=capture_grounding_metadata,
    planner=BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        )
    ),
    instruction=search_instruction,
)
