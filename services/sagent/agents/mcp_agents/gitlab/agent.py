"""Gitlab agent definition.

This agent handles GitLab interactions via:
1. Custom Python tools (direct REST API) — for list/search/create operations
2. MCP tools (@modelcontextprotocol/server-gitlab) — for file content reading

MCP audit results (gitlab.newwave.vn):
  get_file_contents  — works
  search_repositories — broken ('Cannot read properties of undefined')
  Replace broken MCP tools with CUSTOM_TOOLS from tools.py.

Token injection flow:
    root.py callback → fetches user's GitLab PAT from DB
                     → calls make_gitlab_agent(token=pat, base_url=...)
                     → injects token into MCP connection AND session state
                       (session state is read by custom REST tools via tool_context)
"""

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmRequest
from google.adk.planners import BuiltInPlanner
from google.genai.types import ThinkingConfig

from agents.mcp_manager import get_mcp_tools
from agents.mcp_agents.gitlab.tools import CUSTOM_TOOLS
from config.settings import settings
from instructions import gitlab_instruction

GITLAB_BASE_URL = "https://gitlab.newwave.vn/api/v4"


def _make_inject_state_callback(token: str, base_url: str):
    """Returns a before_model_callback that injects GitLab credentials into session state.

    Custom REST tools read from tool_context.state['gitlab:token'] and
    tool_context.state['gitlab:url'] — this callback ensures those values are set.
    """
    async def inject_gitlab_state(
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ):
        callback_context.state["gitlab:token"] = token
        callback_context.state["gitlab:url"] = base_url
        return None

    return inject_gitlab_state


def make_gitlab_agent(token: str, base_url: str = GITLAB_BASE_URL) -> LlmAgent:
    """Create a GitLab agent with the user's PAT injected.

    Combines:
    - CUSTOM_TOOLS: direct REST API tools (reliable, handle auth via session state)
    - MCP tools: @modelcontextprotocol/server-gitlab (for get_file_contents which works)

    Args:
        token: GitLab Personal Access Token (PAT) for the current user.
        base_url: GitLab API base URL. Defaults to newwave.vn.

    Returns:
        An LlmAgent configured with all available GitLab tools.
    """
    mcp_tools = get_mcp_tools("gitlab", token=token)
    all_tools = CUSTOM_TOOLS + mcp_tools

    return LlmAgent(
        name="gitlab",
        model=settings.MODEL_GITLAB,
        description=(
            "Interacts with GitLab to manage repositories, issues, merge requests, "
            "and CI/CD pipelines. Can list projects, browse code, manage issues and MRs."
        ),
        tools=all_tools,
        before_model_callback=_make_inject_state_callback(token, base_url),
        planner=BuiltInPlanner(
            thinking_config=ThinkingConfig(
                include_thoughts=True,
                thinking_budget=1024,
            )
        ),
        instruction=gitlab_instruction,
    )


# Default agent (no token injected — replaced at runtime by root.py callback)
gitlab_agent = LlmAgent(
    name="gitlab",
    model=settings.MODEL_GITLAB,
    description=(
        "Interacts with GitLab to manage repositories, issues, merge requests, "
        "and CI/CD pipelines."
    ),
    tools=[],  # Populated at request time via make_gitlab_agent()
    planner=BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024,
        )
    ),
    instruction=gitlab_instruction,
)
