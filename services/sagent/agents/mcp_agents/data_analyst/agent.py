"""Data analyst sub-agent for BigQuery queries.

This agent handles data exploration and visualisation requests.
It is wrapped as an AgentTool for use by the root agent.

Architecture:
    Root Agent → AgentTool(data_analyst_agent) → BigQuery
                                                     ↓
                                          Query results + widgets

Query attempts are tracked in session state and embedded in responses
via the capture_query_attempts callback for frontend display.
"""

from google.adk.agents import LlmAgent

from agents.mcp_agents.data_analyst.tools import (
    create_chart,
    describe_table,
    list_datasets,
    query_data,
)
from agents.mcp_manager import get_mcp_tools
from callbacks.data_analyst import data_analyst_after_model_callback
from config.settings import settings
from instructions import data_analyst_instruction

_custom_tools = [query_data, list_datasets, describe_table, create_chart]
_mcp_tools = get_mcp_tools("data_analyst")
_data_analyst_tools = _custom_tools + _mcp_tools

data_analyst_agent = LlmAgent(
    name="data_analyst_agent",
    model=settings.MODEL_DATA_ANALYST,
    description=(
        "Queries BigQuery datasets and creates data visualisations. "
        "Use this agent when users ask about data, metrics, analytics, "
        "charts, dashboards, or want to explore business data. "
        "Results appear as interactive charts in the dashboard."
    ),
    tools=_data_analyst_tools,
    instruction=data_analyst_instruction,
    after_model_callback=data_analyst_after_model_callback,
)
