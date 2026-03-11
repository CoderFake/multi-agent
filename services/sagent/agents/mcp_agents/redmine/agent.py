"""Redmine ADK agent definition.

Credential injection flow:
    root.py callback → fetches user's Redmine API key + URL from DB
                     → calls make_redmine_agent(api_key, base_url)
                     → injects values into session state via before_model_callback
                       (redmine:url, redmine:api_key)
                     → tools read those session state keys via ToolContext
"""

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmRequest
from google.adk.planners import BuiltInPlanner
from google.genai.types import ThinkingConfig

from agents.mcp_agents.redmine.tools import ALL_TOOLS
from config.settings import settings
from instructions import redmine_instruction


def _make_inject_state_callback(api_key: str, base_url: str):
    """Return a before_model_callback that injects Redmine credentials into session state.

    Tools read from:
      tool_context.state["redmine:url"]
      tool_context.state["redmine:api_key"]
    """
    async def inject_redmine_state(
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ):
        callback_context.state["redmine:url"]     = base_url
        callback_context.state["redmine:api_key"] = api_key
        return None

    return inject_redmine_state


def make_redmine_agent(api_key: str, base_url: str) -> LlmAgent:
    """Create a Redmine agent with the user's API key injected.

    Args:
        api_key:  Redmine API key for the current user.
        base_url: Redmine instance base URL (e.g. 'https://redmine.example.com').

    Returns:
        An LlmAgent configured with all Redmine tools and credential injection.
    """
    return LlmAgent(
        name="redmine",
        model=settings.MODEL_REDMINE,
        description=(
            "Manages Redmine project management tasks: browsing projects and issues, "
            "creating and updating issues, logging time entries, searching, and more."
        ),
        tools=ALL_TOOLS,
        before_model_callback=_make_inject_state_callback(api_key, base_url),
        planner=BuiltInPlanner(
            thinking_config=ThinkingConfig(
                include_thoughts=True,
                thinking_budget=1024,
            )
        ),
        instruction=redmine_instruction,
    )


# Default agent (no credentials — replaced at runtime by root.py callback)
redmine_agent = LlmAgent(
    name="redmine",
    model=settings.MODEL_REDMINE,
    description=(
        "Manages Redmine project management tasks: browsing projects and issues, "
        "creating and updating issues, logging time entries, and more."
    ),
    tools=[],  # Populated at request time via make_redmine_agent()
    planner=BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        )
    ),
    instruction=redmine_instruction,
)
