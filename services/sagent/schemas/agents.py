"""Agent schemas for API responses."""

from pydantic import BaseModel, Field

class AgentInfo(BaseModel):
    id: str = Field(..., description="Unique ID of the agent (used for toggling)")
    name: str = Field(..., description="Human readable name of the agent")
    description: str = Field(..., description="Description of the agent's capabilities")
    icon: str = Field(default="bot", description="Icon name to display in the UI")
