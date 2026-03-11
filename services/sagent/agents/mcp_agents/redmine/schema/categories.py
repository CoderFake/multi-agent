"""Issue category input schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class ListCategoriesInput(BaseModel):
    """Input for listing issue categories of a project."""
    project_id: str = Field(..., description="Project ID or identifier")


class CreateCategoryInput(BaseModel):
    """Input for creating an issue category.

    API: POST /projects/{project_id}/issue_categories.json
    """
    project_id:     str           = Field(..., description="Project ID or identifier")
    name:           str           = Field(..., description="Category name")
    assigned_to_id: Optional[int] = Field(None, description="Default assignee user ID")
