"""Session CRUD routes.

Routes = validation + service calls + response formatting only.
All business logic lives in services/session_service.py.
"""

import logging

from fastapi import APIRouter, HTTPException

from schemas.common import ErrorResponse
from schemas.sessions import (
    CancelResponse,
    DeleteResponse,
    SessionDetail,
    SessionListResponse,
)
from services.session_service import session_svc

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List sessions",
    description="List all chat sessions for a user, sorted by last updated.",
)
async def list_sessions(user_id: str):
    """List all chat sessions for a user."""
    try:
        return await session_svc.list_user_sessions(user_id)
    except Exception as e:
        return SessionListResponse(sessions=[])


@router.get(
    "/sessions/{session_id}",
    response_model=SessionDetail | ErrorResponse,
    summary="Get session",
    description="Get session details including parsed messages.",
)
async def get_session(session_id: str, user_id: str):
    """Get details of a specific session including messages."""
    try:
        result = await session_svc.get_session_messages(session_id, user_id)
        if result is None:
            return ErrorResponse(error="Session not found")
        return result
    except Exception as e:
        return ErrorResponse(error=str(e))


@router.post(
    "/sessions/{session_id}/cancel",
    response_model=CancelResponse,
    responses={404: {"model": ErrorResponse, "description": "No active execution"}},
    summary="Cancel execution",
    description="Cancel an active agent execution for a session.",
)
async def cancel_session(session_id: str):
    """Cancel an active agent execution for a session."""
    from core.dependencies import get_adk_agent

    adk_agent = get_adk_agent()
    cancelled = await session_svc.cancel_execution(session_id, adk_agent)
    if not cancelled:
        raise HTTPException(status_code=404, detail="No active execution for this session")
    return CancelResponse(status="cancelled")


@router.delete(
    "/sessions/{session_id}",
    response_model=DeleteResponse,
    summary="Delete session",
    description="Delete a specific session.",
)
async def delete_session(session_id: str, user_id: str):
    """Delete a specific session."""
    try:
        await session_svc.delete_session(session_id, user_id)
        return DeleteResponse(success=True)
    except Exception as e:
        return DeleteResponse(success=False, error=str(e))

