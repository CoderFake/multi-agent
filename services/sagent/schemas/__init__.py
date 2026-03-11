"""Pydantic schemas for the sagent API.

Organized by domain. All models are re-exported here for convenience.

Usage:
    from schemas import SessionListResponse, UploadResponse
"""

from schemas.common import ErrorResponse, SuccessResponse
from schemas.debug import (
    DebugEventListResponse,
    DebugSessionDetailResponse,
    DebugSessionListResponse,
    DebugStateResponse,
)
from schemas.health import HealthResponse
from schemas.internal import SyncResponse, SyncResultItem, SyncSummary, SyncTrigger
from schemas.sessions import (
    CancelResponse,
    ChatMessage,
    DeleteResponse,
    SessionDetail,
    SessionListResponse,
    SessionSummary,
)
from schemas.upload import UploadConfigResponse, UploadResponse

__all__ = [
    # Common
    "ErrorResponse",
    "SuccessResponse",
    # Sessions
    "SessionListResponse",
    "SessionSummary",
    "SessionDetail",
    "ChatMessage",
    "CancelResponse",
    "DeleteResponse",
    # Upload
    "UploadConfigResponse",
    "UploadResponse",
    # Health
    "HealthResponse",
    # Internal
    "SyncTrigger",
    "SyncResponse",
    "SyncSummary",
    "SyncResultItem",
    # Debug
    "DebugSessionDetailResponse",
    "DebugEventListResponse",
    "DebugStateResponse",
    "DebugSessionListResponse",
]

