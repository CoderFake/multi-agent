"""Wiki page input schemas."""

from typing import Optional
from pydantic import BaseModel, Field
from agents.common.form_schemas import DynamicDropdownField, RichTextField


class ListWikiPagesInput(BaseModel):
    """Input for listing wiki pages of a project."""
    project_id: str = Field(..., description="Project ID or identifier")


class GetWikiPageInput(BaseModel):
    """Input for fetching a specific wiki page."""
    project_id: str           = Field(..., description="Project ID or identifier")
    title:      str           = Field(..., description="Wiki page title (e.g. 'UsersGuide')")
    version:    Optional[int] = Field(None, description="Specific version number (omit for latest)")


class UpdateWikiPageInput(BaseModel):
    """Input for determining wiki page fields"""
    project_id: str           = DynamicDropdownField("Project ID or identifier", fetch_action="fetch_projects")
    title:      str           = Field(..., description="Wiki page title")
    text:       str           = RichTextField("Wiki page content (required even for updates)")
    comments:   Optional[str] = Field(None, description="Change note")
    version:    Optional[int] = Field(None, description="Current version for conflict detection")


class DeleteWikiPageInput(BaseModel):
    """Input for deleting a wiki page."""
    project_id: str = Field(..., description="Project ID or identifier")
    title:      str = Field(..., description="Wiki page title to delete")
