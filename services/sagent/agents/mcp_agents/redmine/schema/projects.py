"""Project-related input schemas."""

from typing import ClassVar, List, Optional
from pydantic import BaseModel, Field
from agents.common.form_schemas import DynamicDropdownField, RichTextField


class ListProjectsInput(BaseModel):
    """Input for listing Redmine projects."""
    include: Optional[str] = Field(None, description="Extra data to include: trackers,issue_categories,enabled_modules")
    limit:   int           = Field(100, description="Max results")


class GetProjectInput(BaseModel):
    """Input for fetching a single Redmine project."""
    project_id: str = Field(..., description="Project ID number or identifier string")


class CreateProjectInput(BaseModel):
    """Input for creating a Redmine project.

    API: POST /projects.json
    """

    form_meta: ClassVar[dict] = {
        "dynamic_fields": ["parent_id", "tracker_ids"],
    }

    name:           str                = Field(..., description="Project name")
    identifier:     str                = Field(..., description="Slug (lowercase, hyphens)")
    description:      Optional[str] = RichTextField("Project description", default=None)
    homepage:         Optional[str] = Field(None, description="Homepage URL")
    is_public:        Optional[bool] = Field(True, description="Publicly accessible")
    parent_id:        Optional[int] = DynamicDropdownField("Parent Project ID", fetch_action="fetch_projects", default=None)
    inherit_members:  Optional[bool] = Field(False, description="Inherit members from parent")
    default_assignee_id: Optional[int] = DynamicDropdownField("Default Assignee ID", fetch_action="fetch_members", default=None)


class UpdateProjectInput(BaseModel):
    """Input for updating a Redmine project.

    API: PUT /projects/{id}.json
    """
    project_id:     str                = Field(..., description="Project ID or identifier to update")
    name:             Optional[str] = Field(None, description="New name of the project")
    description:      Optional[str] = RichTextField("New description", default=None)
    homepage:         Optional[str] = Field(None, description="New homepage URL")
    is_public:        Optional[bool] = Field(None, description="Publicly accessible")
    parent_id:        Optional[int] = DynamicDropdownField("Parent Project ID", fetch_action="fetch_projects", default=None)
    inherit_members:  Optional[bool] = Field(None, description="Inherit members")
    default_assignee_id: Optional[int] = DynamicDropdownField("Default Assignee ID", fetch_action="fetch_members", default=None)


class DeleteProjectInput(BaseModel):
    """Input for deleting a Redmine project."""
    project_id: str = Field(..., description="Project ID or identifier to delete")


class ArchiveProjectInput(BaseModel):
    """Input for archiving/unarchiving a Redmine project."""
    project_id: str  = Field(..., description="Project ID or identifier")
    archive:    bool = Field(True, description="True to archive, False to unarchive")
