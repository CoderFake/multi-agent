"""Watcher input schemas."""

from pydantic import BaseModel, Field


class AddWatcherInput(BaseModel):
    """Input for adding a watcher to an issue."""
    issue_id: int = Field(..., description="Issue ID")
    user_id:  int = Field(..., description="User ID to add as watcher")


class RemoveWatcherInput(BaseModel):
    """Input for removing a watcher from an issue."""
    issue_id: int = Field(..., description="Issue ID")
    user_id:  int = Field(..., description="User ID to remove from watchers")
