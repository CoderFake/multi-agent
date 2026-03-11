"""Time entry update/delete input schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class ListTimeEntriesInput(BaseModel):
    """Input for listing Redmine time entries."""
    project_id: Optional[str] = Field(None, description="Filter by project ID or identifier")
    issue_id:   Optional[int] = Field(None, description="Filter by issue ID")
    user_id:    Optional[int] = Field(None, description="Filter by user ID")
    from_date:  Optional[str] = Field(None, description="Start date YYYY-MM-DD")
    to_date:    Optional[str] = Field(None, description="End date YYYY-MM-DD")
    limit:      int           = Field(25, description="Max results")


class UpdateTimeEntryInput(BaseModel):
    """Input for updating a time entry.

    API: PUT /time_entries/{id}.json
    """
    time_entry_id: int           = Field(..., description="Time entry ID to update")
    issue_id:      Optional[int] = Field(None, description="New issue ID")
    hours:         Optional[float] = Field(None, description="New hours")
    activity_id:   Optional[int] = Field(None, description="New activity ID")
    comments:      Optional[str] = Field(None, description="New comments")
    spent_on:      Optional[str] = Field(None, description="New date YYYY-MM-DD")


class DeleteTimeEntryInput(BaseModel):
    """Input for deleting a time entry."""
    time_entry_id: int = Field(..., description="Time entry ID to delete")
