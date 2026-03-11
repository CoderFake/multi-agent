"""Pydantic input schema for Redmine create_issue tool."""

from typing import ClassVar, List, Optional
from pydantic import BaseModel, Field


class CreateIssueInput(BaseModel):
    """Input schema for creating a Redmine issue.

    API: POST /issues.json
    Required: project_id, subject
    """

    form_meta: ClassVar[dict] = {
        "dynamic_fields": [
            "project_id", "tracker_id", "status_id", "priority_id",
            "assigned_to_id", "category_id", "fixed_version_id",
            "parent_issue_id",
        ],
        "requires_project": True,
    }

    project_id:       str             = Field(..., title="Project", description="Project", json_schema_extra={"dynamic_dropdown": True, "fetch_action": "fetch_projects"})
    subject:          str             = Field(..., title="Subject", description="Issue title / subject")
    description:      Optional[str]   = Field(None, title="Description", description="Detailed description")
    tracker_id:       Optional[int]   = Field(None, title="Tracker", description="Tracker (Bug/Feature/Task…)", json_schema_extra={"dynamic_dropdown": True, "fetch_action": "fetch_trackers"})
    status_id:        Optional[int]   = Field(None, title="Status", description="Status", json_schema_extra={"dynamic_dropdown": True, "fetch_action": "fetch_statuses"})
    priority_id:      Optional[int]   = Field(None, title="Priority", description="Priority", json_schema_extra={"dynamic_dropdown": True, "fetch_action": "fetch_priorities"})
    assigned_to_id:   Optional[int]   = Field(None, title="Assignee", description="Assignee", json_schema_extra={"dynamic_dropdown": True, "fetch_action": "fetch_members", "depends_on": "project_id"})
    category_id:      Optional[int]   = Field(None, title="Category", description="Category", json_schema_extra={"dynamic_dropdown": True, "fetch_action": "fetch_categories", "depends_on": "project_id"})
    fixed_version_id: Optional[int]   = Field(None, title="Target Version", description="Target version", json_schema_extra={"dynamic_dropdown": True, "fetch_action": "fetch_versions", "depends_on": "project_id"})
    parent_issue_id:  Optional[int]   = Field(None, title="Parent Issue", description="Parent issue ID", json_schema_extra={"dynamic_dropdown": True, "fetch_action": "fetch_issues", "depends_on": "project_id"})
    is_private:       Optional[bool]  = Field(None, description="Private issue")
    estimated_hours:  Optional[float] = Field(None, description="Estimated hours")
    start_date:       Optional[str]   = Field(
        None,
        description="Start date",
        json_schema_extra={"format": "date"},
    )
    due_date:         Optional[str]   = Field(
        None,
        description="Due date",
        json_schema_extra={"format": "date"},
    )
    done_ratio:       Optional[int]   = Field(None, description="Completion % (0-100)")
    watcher_user_ids: list | None = Field(None, description="Watcher user IDs")
