"""
routes/chat_history.py — REST API for chat sessions & messages.

All endpoints require Firebase auth via Depends(get_current_user).
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_user
from models.user import User
from services.chat_history_service import chat_history_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat-history"])


# ── Request / Response schemas ─────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    title: Optional[str] = None


class UpdateTitleRequest(BaseModel):
    title: str


class AddMessageRequest(BaseModel):
    query: str
    response: Optional[str] = None
    session_id: Optional[str] = None  # if omitted, creates a new session


class UpdateResponseRequest(BaseModel):
    response: str


# ── Session endpoints ──────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List chat sessions for the authenticated user (newest first)."""
    sessions = await chat_history_service.list_sessions(db, user.id, limit, offset)
    return {"sessions": sessions, "count": len(sessions)}


@router.post("/sessions")
async def create_session(
    body: CreateSessionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new empty chat session."""
    session = await chat_history_service.create_session(db, user.id, title=body.title)
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a session with all its messages."""
    session = await chat_history_service.get_session(db, session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await chat_history_service.get_messages(db, session_id, user.id)
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "messages": messages,
    }


@router.patch("/sessions/{session_id}")
async def update_session_title(
    session_id: str,
    body: UpdateTitleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename a chat session."""
    ok = await chat_history_service.update_session_title(db, session_id, user.id, body.title)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "updated"}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a session and all its messages."""
    ok = await chat_history_service.delete_session(db, session_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted"}


@router.delete("/sessions")
async def delete_all_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete ALL sessions for the authenticated user."""
    count = await chat_history_service.delete_all_sessions(db, user.id)
    return {"status": "deleted", "count": count}


# ── Message endpoints ──────────────────────────────────────────────────

@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a session."""
    messages = await chat_history_service.get_messages(db, session_id, user.id)
    return {"messages": messages, "count": len(messages)}


@router.post("/messages")
async def add_message(
    body: AddMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a message (query + optional response) to a session.
    If session_id is omitted, a new session is created automatically.
    """
    session = await chat_history_service.get_or_create_session(
        db, user.id, session_id=body.session_id
    )
    msg = await chat_history_service.add_message(
        db, session.id, user.id, query=body.query, response=body.response
    )
    if not msg:
        raise HTTPException(status_code=500, detail="Failed to add message")
    return {
        "session_id": session.id,
        "message_id": msg.id,
        "order": msg.order,
        "title": session.title,
    }


@router.patch("/messages/{message_id}")
async def update_message_response(
    message_id: str,
    body: UpdateResponseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the response of an existing message."""
    ok = await chat_history_service.update_message_response(db, message_id, body.response)
    if not ok:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"status": "updated"}
