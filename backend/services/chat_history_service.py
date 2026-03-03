"""
services/chat_history_service.py — CRUD for ChatSession & ChatMessage.

All operations scoped to user_id for security.
"""
import logging
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.chat import ChatSession, ChatMessage

logger = logging.getLogger(__name__)


class ChatHistoryService:
    """Service for managing chat sessions and messages."""

    # ── Sessions ───────────────────────────────────────────────────────

    async def create_session(
        self,
        db: AsyncSession,
        user_id: str,
        title: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ChatSession:
        """Create a new chat session for a user."""
        kwargs: Dict[str, Any] = {"user_id": user_id}
        if title:
            kwargs["title"] = title
        if session_id:
            kwargs["id"] = session_id
        session = ChatSession(**kwargs)
        db.add(session)
        await db.flush()
        logger.info("Created chat session %s for user %s", session.id, user_id)
        return session

    async def get_session(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str,
    ) -> Optional[ChatSession]:
        """Get a single session (with messages) belonging to user."""
        result = await db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List sessions for a user (newest first), with message count."""
        result = await db.execute(
            select(
                ChatSession.id,
                ChatSession.title,
                ChatSession.created_at,
                ChatSession.updated_at,
                func.count(ChatMessage.id).label("message_count"),
            )
            .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
            .where(ChatSession.user_id == user_id)
            .group_by(ChatSession.id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = result.all()
        return [
            {
                "id": r.id,
                "title": r.title,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "message_count": r.message_count,
            }
            for r in rows
        ]

    async def update_session_title(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str,
        title: str,
    ) -> bool:
        """Rename a session."""
        session = await self._get_session_owned(db, session_id, user_id)
        if not session:
            return False
        session.title = title
        await db.flush()
        return True

    async def delete_session(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str,
    ) -> bool:
        """Delete a session and all its messages (cascade)."""
        session = await self._get_session_owned(db, session_id, user_id)
        if not session:
            return False
        await db.delete(session)
        await db.flush()
        logger.info("Deleted session %s for user %s", session_id, user_id)
        return True

    async def delete_all_sessions(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> int:
        """Delete ALL sessions (and messages) for a user. Returns count deleted."""
        result = await db.execute(
            select(func.count(ChatSession.id)).where(ChatSession.user_id == user_id)
        )
        count = result.scalar() or 0
        await db.execute(
            delete(ChatSession).where(ChatSession.user_id == user_id)
        )
        await db.flush()
        logger.info("Deleted %d sessions for user %s", count, user_id)
        return count

    # ── Messages ───────────────────────────────────────────────────────

    async def add_message(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str,
        query: str,
        response: Optional[str] = None,
    ) -> Optional[ChatMessage]:
        """
        Append a query+response row to a session.
        Auto-increments order. Auto-generates title from first query.
        Returns the new ChatMessage or None if session not found.
        """
        session = await self._get_session_owned(db, session_id, user_id)
        if not session:
            return None

        # Next order number
        result = await db.execute(
            select(func.coalesce(func.max(ChatMessage.order), 0))
            .where(ChatMessage.session_id == session_id)
        )
        next_order = (result.scalar() or 0) + 1

        msg = ChatMessage(
            session_id=session_id,
            order=next_order,
            query=query,
            response=response,
        )
        db.add(msg)

        # Auto-title from first message
        if not session.title and next_order == 1:
            session.title = query[:80] + ("…" if len(query) > 80 else "")

        await db.flush()
        return msg

    async def update_message_response(
        self,
        db: AsyncSession,
        message_id: str,
        response: str,
    ) -> bool:
        """Update the response field of an existing message."""
        msg = await db.get(ChatMessage, message_id)
        if not msg:
            return False
        msg.response = response
        await db.flush()
        return True

    async def get_messages(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all messages in a session (ordered)."""
        # Verify ownership
        session = await self._get_session_owned(db, session_id, user_id)
        if not session:
            return []

        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.order.asc())
        )
        rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "order": r.order,
                "query": r.query,
                "response": r.response,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    # ── Get or create session ──────────────────────────────────────────

    async def get_or_create_session(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> ChatSession:
        """Get existing session or create a new one."""
        if session_id:
            session = await self._get_session_owned(db, session_id, user_id)
            if session:
                return session
        return await self.create_session(db, user_id, session_id=session_id)

    # ── Internal ───────────────────────────────────────────────────────

    async def _get_session_owned(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str,
    ) -> Optional[ChatSession]:
        """Fetch a session only if it belongs to user_id."""
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()


# Global singleton
chat_history_service = ChatHistoryService()
