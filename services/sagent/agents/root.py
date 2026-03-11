"""Root agent definition.

This is the main agent that users interact with. It orchestrates:
- File tools (list_files, read_file) for uploaded documents
- Web search via AgentTool delegation to the search agent
- Team knowledge retrieval via AgentTool delegation to the team knowledge agent
"""

import logging

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.llm_agent import LlmRequest
from google.adk.planners import BuiltInPlanner
from google.adk.tools.agent_tool import AgentTool
from google.genai.types import ThinkingConfig

from agents import SUB_AGENTS
from agents.mcp_agents.gitlab.agent import make_gitlab_agent
from agents.mcp_agents.redmine.agent import make_redmine_agent
from callbacks import (
    auto_generate_session_title,
    inject_artifact_content,
    inject_user_context,
)
from config.settings import settings
from instructions import root_instruction
from tools import list_files, read_file
from services.oauth import get_oauth_connection

logger = logging.getLogger(__name__)


async def combined_before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
):
    """Combined before_model_callback that runs multiple callbacks.

    Chains:
    1. inject_user_context - Sets up user teams and corpora in state
    2. inject_artifact_content - Injects binary artifacts into LLM context

    TODO: Refactor to ADK Plugin when ag-ui-adk supports plugins.
    ADK's Plugin system handles callback chaining elegantly, but the current
    ag-ui-adk.ADKAgent middleware doesn't expose the plugins parameter.
    """
    await inject_user_context(callback_context, llm_request)
    await inject_artifact_content(callback_context, llm_request)

    headers = callback_context.state.get("headers", {})
    enabled_agents_header = headers.get("x-enabled-agents")
    enabled_list = [t.strip() for t in enabled_agents_header.split(",")] if enabled_agents_header else []
    
    if "gitlab" in llm_request.tools_dict and ("gitlab" in enabled_list or not enabled_agents_header):
        user_id = callback_context.state.get("user_id") or (callback_context.session.user_id if callback_context.session else None)
        callback_context.state["user_id"] = user_id

        if user_id:
            try:
                gitlab_conn = get_oauth_connection(user_id=user_id, provider="gitlab")
                if gitlab_conn:
                    pat = gitlab_conn.access_token
                    base_url = getattr(gitlab_conn, "base_url", None) or "https://gitlab.newwave.vn/api/v4"
                    llm_request.tools_dict["gitlab"] = AgentTool(agent=make_gitlab_agent(token=pat, base_url=base_url))
                    logger.info("GitLab agent rebuilt with authenticated PAT for user %s", user_id)
                else:
                    del llm_request.tools_dict["gitlab"]
                    logger.warning("GitLab agent removed: no PAT connection found for user %s", user_id)
            except Exception as e:
                logger.error("Failed to build GitLab agent for user %s: %s", user_id, e)
                del llm_request.tools_dict["gitlab"]
        else:
            logger.warning("GitLab agent: cannot resolve user_id — removing from tools")
            del llm_request.tools_dict["gitlab"]

    if "redmine" in llm_request.tools_dict and ("redmine" in enabled_list or not enabled_agents_header):
        user_id = callback_context.state.get("user_id") or (callback_context.session.user_id if callback_context.session else None)

        if user_id:
            try:
                redmine_conn = get_oauth_connection(user_id=user_id, provider="redmine")
                if redmine_conn:
                    api_key  = redmine_conn.access_token
                    base_url = redmine_conn.scopes or ""
                    if base_url:
                        llm_request.tools_dict["redmine"] = AgentTool(agent=make_redmine_agent(api_key=api_key, base_url=base_url))
                        logger.info("Redmine agent rebuilt with authenticated key for user %s", user_id)
                    else:
                        del llm_request.tools_dict["redmine"]
                        logger.warning("Redmine agent removed: no base_url found for user %s", user_id)
                else:
                    del llm_request.tools_dict["redmine"]
                    logger.warning("Redmine agent removed: no API key connection found for user %s", user_id)
            except Exception as e:
                logger.error("Failed to build Redmine agent for user %s: %s", user_id, e)
                del llm_request.tools_dict["redmine"]
        else:
            logger.warning("Redmine agent: cannot resolve user_id — removing from tools")
            del llm_request.tools_dict["redmine"]

    active_tools = []
    for name, tool in list(llm_request.tools_dict.items()):
        if enabled_agents_header is not None and hasattr(tool, "agent") and name not in enabled_list:
            continue
        active_tools.append(tool)

    llm_request.tools_dict.clear()
    if llm_request.config:
        llm_request.config.tools = []
    
    llm_request.append_tools(active_tools)

    return None


root_agent = LlmAgent(
    name="root_agent",
    model=settings.MODEL_ROOT,
    description="Enterprise knowledge assistant that answers questions from internal documents and data.",
    tools=[
        list_files,
        read_file,
    ] + [AgentTool(agent=a) for a in SUB_AGENTS],
    before_model_callback=combined_before_model_callback,
    after_agent_callback=auto_generate_session_title,
    planner=BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=True,
            thinking_budget=2048,
        )
    ),
    instruction=root_instruction,
)
