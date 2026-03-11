"""Issue relation input schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class ListRelationsInput(BaseModel):
    """Input for listing relations of an issue."""
    issue_id: int = Field(..., description="Issue ID")


class CreateRelationInput(BaseModel):
    """Input for creating an issue relation.

    API: POST /issues/{issue_id}/relations.json
    """
    issue_id:      int           = Field(..., description="Source issue ID")
    issue_to_id:   int           = Field(..., description="Target issue ID")
    relation_type: Optional[str] = Field(
        "relates",
        description="Relation type: relates, duplicates, duplicated, blocks, blocked, precedes, follows, copied_to, copied_from",
    )
    delay:         Optional[int] = Field(None, description="Delay in days (for precedes/follows)")


class DeleteRelationInput(BaseModel):
    """Input for deleting an issue relation."""
    relation_id: int = Field(..., description="Relation ID to delete")
