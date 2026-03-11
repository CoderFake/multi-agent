"""Session request/response schemas."""

from pydantic import BaseModel, Field


class SessionSummary(BaseModel):
    """A single session in the session list."""

    id: str = Field(..., description="Session identifier")
    title: str = Field(default="New conversation", description="Session title")
    lastUpdated: float | None = Field(default=None, description="Last update timestamp")


class SessionListResponse(BaseModel):
    """Response for listing user sessions."""

    sessions: list[SessionSummary] = Field(
        default_factory=list, description="User's chat sessions, sorted by last updated"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sessions": [
                        {
                            "id": "sess_abc123",
                            "title": "Python debugging help",
                            "lastUpdated": 1710000000.0,
                        }
                    ]
                }
            ]
        }
    }


class ChatMessage(BaseModel):
    """A single chat message (user or assistant)."""

    role: str = Field(..., description="Message role: 'user' or 'model'", examples=["user", "model"])
    content: str = Field(..., description="Message content (may contain semantic tags)")
    timestamp: float | None = Field(default=None, description="Event timestamp")
    invocationId: str | None = Field(default=None, description="ADK invocation ID for message grouping")


class SessionDetail(BaseModel):
    """Response for getting a single session with messages."""

    id: str = Field(..., description="Session identifier")
    messages: list[ChatMessage] = Field(default_factory=list, description="Ordered chat messages")
    lastUpdated: float | None = Field(default=None, description="Last update timestamp")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "sess_abc123",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Hello",
                            "timestamp": 1710000000.0,
                            "invocationId": "inv_001",
                        },
                        {
                            "role": "model",
                            "content": "Hi! How can I help?",
                            "timestamp": 1710000001.0,
                            "invocationId": "inv_001",
                        },
                    ],
                    "lastUpdated": 1710000001.0,
                }
            ]
        }
    }


class CancelResponse(BaseModel):
    """Response for cancelling an active execution."""

    status: str = Field(default="cancelled", description="Cancellation status")


class DeleteResponse(BaseModel):
    """Response for deleting a session."""

    success: bool = Field(..., description="Whether the deletion succeeded")
    error: str | None = Field(default=None, description="Error message if failed")

