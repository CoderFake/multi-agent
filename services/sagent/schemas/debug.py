"""Debug endpoint schemas — session inspection and diagnostics."""

from typing import Any

from pydantic import BaseModel, Field


class SerializedEvent(BaseModel):
    """A serialized ADK event for debugging."""

    id: str | None = Field(default=None, description="Event ID")
    author: str | None = Field(default=None, description="Event author")
    invocation_id: str | None = Field(default=None, description="Invocation ID")
    timestamp: float | None = Field(default=None, description="Event timestamp")
    content: dict[str, Any] | None = Field(default=None, description="Event content with role and parts")
    actions: dict[str, Any] | None = Field(default=None, description="State and artifact deltas")


class DebugSessionDetailResponse(BaseModel):
    """Full session details for debugging."""

    id: str = Field(..., description="Session identifier")
    app_name: str = Field(..., description="Application name")
    user_id: str = Field(..., description="User identifier")
    state: dict[str, Any] = Field(default_factory=dict, description="Current session state")
    last_update_time: float | None = Field(default=None, description="Last update timestamp")
    event_count: int = Field(default=0, ge=0, description="Total number of events")
    events: list[SerializedEvent] = Field(default_factory=list, description="All session events")


class DebugEventListResponse(BaseModel):
    """Paginated event list for debugging."""

    session_id: str = Field(..., description="Session identifier")
    total_events: int = Field(..., ge=0, description="Total events in session")
    offset: int = Field(default=0, ge=0, description="Current offset")
    limit: int = Field(default=50, ge=1, description="Page size")
    events: list[SerializedEvent] = Field(default_factory=list, description="Events for this page")


class DebugStateResponse(BaseModel):
    """Session state for debugging."""

    session_id: str = Field(..., description="Session identifier")
    state: dict[str, Any] = Field(default_factory=dict, description="Current session state")


class DebugSessionSummary(BaseModel):
    """Minimal session info for debug listing."""

    id: str = Field(..., description="Session identifier")
    last_update_time: float | None = Field(default=None, description="Last update timestamp")


class DebugSessionListResponse(BaseModel):
    """List of sessions for debugging."""

    user_id: str = Field(..., description="User identifier")
    session_count: int = Field(default=0, ge=0, description="Total sessions")
    sessions: list[DebugSessionSummary] = Field(default_factory=list, description="Sessions sorted by last update")

