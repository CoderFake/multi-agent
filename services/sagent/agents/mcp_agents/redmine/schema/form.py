"""Form-related input schemas (form context + request user input)."""

from typing import Optional
from pydantic import BaseModel, Field


class FetchFormContextInput(BaseModel):
    """Input for pre-fetching dynamic dropdown options before rendering a form."""
    tool_name:  str           = Field(..., description="Which tool to render a form for: 'create_issue' or 'log_time'")
    project_id: Optional[str] = Field(None, description="Redmine project identifier (required for create_issue and log_time)")


class RequestUserInputInput(BaseModel):
    """Triggers a CopilotKit renderAndWaitForResponse form on the frontend.

    ALWAYS auto-fetches dropdown data from Redmine — the LLM should NOT
    try to construct dropdown data manually. Just pass tool_name + project_id.
    """
    tool_name:     str           = Field(..., description="Tool to render a form for: 'create_issue' or 'log_time'")
    project_id:    Optional[str] = Field(None, description="Project ID or slug — needed for member list and open issues")
    options:       dict          = Field(default_factory=dict, description="Ignored — dropdown data is always auto-fetched")
    form_defaults: dict          = Field(default_factory=dict, description="Pre-fill values, e.g. {subject: 'Fix bug', project_id: '116'}")
