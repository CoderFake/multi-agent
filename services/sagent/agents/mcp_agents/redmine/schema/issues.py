"""Issue-related input schemas."""

from typing import ClassVar, Optional
from pydantic import BaseModel, Field
from typing import Optional, List
from agents.common.form_schemas import DynamicDropdownField, RichTextField


class ListIssuesInput(BaseModel):
    """Input for listing Redmine issues with optional filters."""
    project_id:      Optional[str] = Field(None, description="Filter by project ID or identifier")
    status_id:       Optional[str] = Field(None, description="'open', 'closed', '*', or a numeric status ID")
    assigned_to_id:  Optional[str] = Field(None, description="Filter by assignee user ID or 'me'")
    tracker_id:      Optional[int] = Field(None, description="Filter by tracker ID")
    limit:           int           = Field(25,   description="Max results (default 25, max 100)")
    offset:          int           = Field(0,    description="Offset for pagination")


class GetIssueInput(BaseModel):
    """Input for fetching a single Redmine issue by ID."""
    issue_id: int             = Field(..., description="Redmine issue ID")
    include:  Optional[str]   = Field(None, description="Comma-separated includes: journals,attachments,watchers,relations,children")


class CreateIssueInput(BaseModel):
    """Input for creating a new Redmine issue."""

    form_meta: ClassVar[dict] = {
        "dynamic_fields": [
            "project_id", "tracker_id", "status_id", "priority_id",
            "category_id", "fixed_version_id", "assigned_to_id",
            "parent_issue_id",
        ],
    }

    project_id:       str           = DynamicDropdownField("Project ID or identifier string", fetch_action="fetch_projects")
    subject:          str           = Field(..., description="Short summary of the issue")
    tracker_id:       int           = DynamicDropdownField("Tracker ID", fetch_action="fetch_trackers", depends_on="project_id")
    status_id:        Optional[int] = DynamicDropdownField("Status ID", fetch_action="fetch_statuses", depends_on="project_id", default=None)
    priority_id:      Optional[int] = DynamicDropdownField("Priority ID", fetch_action="fetch_priorities", depends_on="project_id", default=None)
    description:      Optional[str] = RichTextField("Detailed description", default=None)
    category_id:      Optional[int] = DynamicDropdownField("Category ID", fetch_action="fetch_categories", depends_on="project_id", default=None)
    fixed_version_id: Optional[int] = DynamicDropdownField("Target Version ID", fetch_action="fetch_versions", depends_on="project_id", default=None)
    assigned_to_id:   Optional[int] = DynamicDropdownField("Assignee User ID", fetch_action="fetch_members", depends_on="project_id", default=None)
    parent_issue_id:  Optional[int] = DynamicDropdownField("Parent Issue ID", fetch_action="fetch_issues", depends_on="project_id", default=None)
    due_date:         Optional[str] = Field(None, title="Due Date", description="Due date", json_schema_extra={"format": "date"})
    done_ratio:       Optional[int] = Field(None, title="Done Ratio", description="Completion % (0-100)")
    notes:            Optional[str] = Field(None, title="Notes", description="Note for this change")


class UpdateIssueInput(BaseModel):
    """Input for updating an existing Redmine issue."""

    form_meta: ClassVar[dict] = {
        "dynamic_fields": [
            "status_id", "priority_id", "assigned_to_id",
            "category_id", "fixed_version_id", "parent_issue_id",
        ],
    }

    issue_id:         int           = Field(..., title="Issue ID", description="Issue to update")
    subject:          Optional[str] = Field(None, title="Subject", description="New subject")
    description:      Optional[str] = RichTextField("New description", default=None)
    status_id:        Optional[int] = DynamicDropdownField("Status", fetch_action="fetch_statuses", default=None)
    priority_id:      Optional[int] = DynamicDropdownField("Priority", fetch_action="fetch_priorities", default=None)
    assigned_to_id:   Optional[int] = DynamicDropdownField("Assignee", fetch_action="fetch_members", depends_on="project_id", default=None)
    category_id:      Optional[int] = DynamicDropdownField("Category", fetch_action="fetch_categories", depends_on="project_id", default=None)
    fixed_version_id: Optional[int] = DynamicDropdownField("Target Version", fetch_action="fetch_versions", depends_on="project_id", default=None)
    parent_issue_id:  Optional[int] = DynamicDropdownField("Parent Issue", fetch_action="fetch_issues", depends_on="project_id", default=None)
    due_date:         Optional[str] = Field(None, title="Due Date", description="Due date", json_schema_extra={"format": "date"})
    done_ratio:       Optional[int] = Field(None, title="Done Ratio", description="Completion % (0-100)")
    notes:            Optional[str] = Field(None, title="Notes", description="Note for this change")


class DeleteIssueInput(BaseModel):
    """Input for deleting a Redmine issue."""
    issue_id: int = Field(..., description="ID of the issue to delete")
