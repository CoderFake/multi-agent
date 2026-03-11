"""Version-related input schemas."""

from typing import ClassVar, Optional
from pydantic import BaseModel, Field
from agents.common.form_schemas import DynamicDropdownField, RichTextField


class ListVersionsInput(BaseModel):
    """Input for listing project versions."""
    project_id: str = Field(..., description="Project ID or identifier")


class CreateVersionInput(BaseModel):
    """Input for creating a project version.

    API: POST /projects/{project_id}/versions.json
    """

    form_meta: ClassVar[dict] = {
        "dynamic_fields": ["project_id"],
    }

    project_id:  str           = DynamicDropdownField("Project", fetch_action="fetch_projects")
    name:        str           = Field(..., description="Version name (e.g. v1.0.0)")
    status:      Optional[str] = Field(None, description="Status", json_schema_extra={
        "enum": ["open", "locked", "closed"],
        "enumNames": ["Open", "Locked", "Closed"],
    })
    sharing:     Optional[str] = Field(None, description="Sharing", json_schema_extra={
        "enum": ["none", "descendants", "hierarchy", "tree", "system"],
        "enumNames": ["None", "Descendants", "Hierarchy", "Tree", "System"],
    })
    due_date:    Optional[str] = Field(None, description="Due date", json_schema_extra={"format": "date"})
    description: Optional[str] = RichTextField("Description", default=None)
    wiki_page_title: Optional[str] = Field(None, description="Wiki page to link")
