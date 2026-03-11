"""Pydantic input schema for Redmine log_time (time entry) tool."""

from typing import ClassVar, Optional
from pydantic import BaseModel, Field
from agents.common.form_schemas import DynamicDropdownField


class LogTimeInput(BaseModel):
    """Input schema for logging a time entry to a Redmine issue.

    API: POST /time_entries.json
    Required: issue_id or project_id, hours
    """

    form_meta: ClassVar[dict] = {
        "dynamic_fields": ["project_id", "issue_id", "activity_id"],
        "requires_project": True,
    }

    issue_id:    Optional[int] = DynamicDropdownField("Issue", fetch_action="fetch_issues", depends_on="project_id", default=None)
    project_id:  Optional[str] = DynamicDropdownField("Project", fetch_action="fetch_projects", default=None)
    hours:       float         = Field(..., title="Hours", description="Number of hours logged")
    activity_id: Optional[int] = DynamicDropdownField("Activity Type", fetch_action="fetch_activities", default=None)
    comments:    Optional[str] = Field(None, title="Comments", description="Short description of work")
    spent_on:    Optional[str] = Field(
        None,
        title="Spent On",
        description="Date work was performed",
        json_schema_extra={"format": "date"},
    )
    user_id:     Optional[int] = Field(None, description="Log for another user")
