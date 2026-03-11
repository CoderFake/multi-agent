"""Member-related input schemas."""

from pydantic import BaseModel, Field


class ListMembersInput(BaseModel):
    """Input for listing project members."""
    project_id: str = Field(..., description="Project ID or identifier")
    limit:      int = Field(100, description="Max results")
