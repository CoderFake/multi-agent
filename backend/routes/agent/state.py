"""
Agent State Definition
Combines research-canvas state + MCP-specific state
"""

from typing import List, TypedDict, Literal, Optional
from langgraph.graph import MessagesState


class Resource(TypedDict):
    """
    Represents a resource. Give it a good title and a short description.
    """
    url: str
    title: str
    description: str


class Log(TypedDict):
    """
    Represents a log of an action performed by the agent.
    Following research-canvas pattern.
    """
    message: str
    done: bool


class ThinkingStep(TypedDict, total=False):
    """Current thinking step of the agent (MCP-specific)"""
    type: Literal["analysis", "execution"]
    message: str
    status: Literal["active", "completed"]


class PlanTask(TypedDict):
    """A task in the MCP execution plan"""
    id: str
    name: str
    toolName: str
    status: Literal["pending", "running", "completed", "error"]


class AgentState(MessagesState):
    """
    Combined state: research-canvas fields + MCP fields
    """
    # Model being used
    model: str
    
    # Research-canvas fields
    research_question: str
    report: str
    resources: List[Resource]
    
    # Shared: Real-time progress logs (used by both research + MCP)
    logs: List[Log]
    
    # MCP-specific fields
    thinking_step: Optional[ThinkingStep]
    execution_plan: List[PlanTask]
