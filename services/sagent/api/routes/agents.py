"""Agents route."""

from fastapi import APIRouter

from agent import root_agent
from schemas.agents import AgentInfo
from common.constants import AGENT_ICONS, AGENT_NAMES

router = APIRouter()

@router.get(
    "/agents",
    response_model=list[AgentInfo],
    summary="List Sub-Agents",
    description="Returns the list of available sub-agents registered in the root agent.",
)
async def list_agents():
    """List available agents by inspecting root_agent.tools."""
    agents = []
    for sub_agent_tool in root_agent.tools:
        if hasattr(sub_agent_tool, "agent"):
            sub_agent = sub_agent_tool.agent
            
            name_parts = sub_agent.name.replace("_agent", "").split("_")
            default_name = " ".join(part.capitalize() for part in name_parts)
            human_name = AGENT_NAMES.get(sub_agent.name, default_name)
                
            icon = next((val for key, val in AGENT_ICONS.items() if key in sub_agent.name), "bot")
                
            agents.append(
                AgentInfo(
                    id=sub_agent.name,
                    name=human_name,
                    description=sub_agent.description,
                    icon=icon,
                )
            )
            
    return agents
