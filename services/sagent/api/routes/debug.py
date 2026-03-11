"""Debug endpoints — for inspecting sessions, events, and state."""

import logging

from fastapi import APIRouter

from schemas.common import ErrorResponse
from schemas.debug import (
    DebugEventListResponse,
    DebugSessionDetailResponse,
    DebugSessionListResponse,
    DebugStateResponse,
)
from services.session_service import session_svc

router = APIRouter(prefix="/api/debug")
logger = logging.getLogger("agent.debug")


@router.get(
    "/sessions/{session_id}",
    response_model=DebugSessionDetailResponse | ErrorResponse,
    summary="Debug session",
    description="Get full session details including all events and state.",
)
async def debug_session(session_id: str, user_id: str):
    """Get full session details including all events and state."""
    try:
        result = await session_svc.get_debug_session(session_id, user_id)
        if result is None:
            return ErrorResponse(error="Session not found")
        return result
    except Exception as e:
        logger.exception(f"Error fetching debug session {session_id}")
        return ErrorResponse(error=str(e))


@router.get(
    "/sessions/{session_id}/events",
    response_model=DebugEventListResponse | ErrorResponse,
    summary="Debug events",
    description="Get paginated events for a session.",
)
async def debug_session_events(
    session_id: str,
    user_id: str,
    limit: int = 50,
    offset: int = 0,
):
    """Get paginated events for a session."""
    try:
        result = await session_svc.get_debug_events(session_id, user_id, limit, offset)
        if result is None:
            return ErrorResponse(error="Session not found")
        return result
    except Exception as e:
        logger.exception(f"Error fetching events for session {session_id}")
        return ErrorResponse(error=str(e))


@router.get(
    "/sessions/{session_id}/state",
    response_model=DebugStateResponse | ErrorResponse,
    summary="Debug state",
    description="Get only the current state for a session.",
)
async def debug_session_state(session_id: str, user_id: str):
    """Get only the current state for a session."""
    try:
        result = await session_svc.get_debug_state(session_id, user_id)
        if result is None:
            return ErrorResponse(error="Session not found")
        return result
    except Exception as e:
        logger.exception(f"Error fetching state for session {session_id}")
        return ErrorResponse(error=str(e))


@router.get(
    "/sessions",
    response_model=DebugSessionListResponse | ErrorResponse,
    summary="Debug list sessions",
    description="List all sessions for a user with their IDs for debugging.",
)
async def debug_list_sessions(user_id: str):
    """List all sessions for a user with their IDs for debugging."""
    try:
        return await session_svc.list_debug_sessions(user_id)
    except Exception as e:
        logger.exception(f"Error listing sessions for user {user_id}")
        return ErrorResponse(error=str(e))


@router.get("/logging")
async def debug_logging_config():
    """Get current logging configuration."""
    return get_logging_status()

