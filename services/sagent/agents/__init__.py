"""Agents package for the multi-agent system.

Contains:
- root_agent: Main orchestrator agent
- team_knowledge_agent: Document retrieval via Milvus retrieval microservice
- search_agent: Web search via Google Search
- data_analyst_agent: BigQuery queries and visualisations
"""

import importlib
import logging
from pathlib import Path

from agents.rag import team_knowledge_agent

logger = logging.getLogger(__name__)

SUB_AGENTS = [
    team_knowledge_agent,
]

_mcp_agents_dir = Path(__file__).parent / "mcp_agents"
if _mcp_agents_dir.exists():
    for agent_dir in _mcp_agents_dir.iterdir():
        if agent_dir.is_dir() and not agent_dir.name.startswith("__"):
            agent_name = agent_dir.name
            try:
                module = importlib.import_module(f"agents.mcp_agents.{agent_name}.agent")
                
                target_var = f"{agent_name}_agent"
                if hasattr(module, target_var):
                    SUB_AGENTS.append(getattr(module, target_var))
                    logger.debug(f"Auto-loaded MCP sub-agent: {target_var}")
                else:
                    logger.warning(f"Could not find {target_var} in {agent_name}.agent")
            except Exception as e:
                logger.error(f"Failed to auto-load MCP agent '{agent_name}': {e}")

from agents.root import root_agent

__all__ = [
    "SUB_AGENTS",
    "root_agent",
]
