"""Session business logic — list, get, cancel, delete sessions.

All session-related business logic lives here. Route handlers call these
methods and format the response; they never query session_service directly.

Usage:
    from services.session_service import session_svc

    sessions = await session_svc.list_user_sessions(user_id)
"""

import json
import logging

from common.constants import APP_NAME
from core.dependencies import session_service
from services.titles import get_titles_bulk
from utils.semantic_tags import (
    THOUGHT_TAG_CLOSE,
    THOUGHT_TAG_OPEN,
    TOOL_RESULT_TAG_CLOSE,
    TOOL_RESULT_TAG_OPEN,
    TOOL_TAG_CLOSE,
    TOOL_TAG_OPEN,
)

logger = logging.getLogger(__name__)


def _serialize_event(event) -> dict:
    """Serialize an ADK event to a JSON-compatible dict."""
    result = {
        "id": getattr(event, "id", None),
        "author": getattr(event, "author", None),
        "invocation_id": getattr(event, "invocation_id", None),
        "timestamp": getattr(event, "timestamp", None),
    }

    if event.content:
        result["content"] = {"role": event.content.role, "parts": []}
        for part in event.content.parts or []:
            part_data = {}
            if hasattr(part, "text") and part.text:
                part_data["text"] = part.text
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                part_data["function_call"] = {
                    "name": getattr(fc, "name", None),
                    "args": dict(fc.args) if hasattr(fc, "args") and fc.args else {},
                    "id": getattr(fc, "id", None),
                }
            if hasattr(part, "function_response") and part.function_response:
                fr = part.function_response
                part_data["function_response"] = {
                    "name": getattr(fr, "name", None),
                    "response": fr.response if hasattr(fr, "response") else None,
                    "id": getattr(fr, "id", None),
                }
            if part_data:
                result["content"]["parts"].append(part_data)

    if hasattr(event, "actions") and event.actions:
        actions = event.actions
        result["actions"] = {
            "state_delta": dict(actions.state_delta)
            if hasattr(actions, "state_delta") and actions.state_delta
            else {},
            "artifact_delta": dict(actions.artifact_delta)
            if hasattr(actions, "artifact_delta") and actions.artifact_delta
            else {},
        }

    return result


class SessionService:
    """Business logic for chat session operations."""

    async def list_user_sessions(self, user_id: str) -> dict:
        """List all chat sessions for a user with titles."""
        response = await session_service.list_sessions(
            app_name=APP_NAME, user_id=user_id
        )

        session_ids = [s.id for s in response.sessions]
        titles = get_titles_bulk(session_ids)

        sessions = []
        for session in response.sessions:
            title = titles.get(session.id, "New conversation")
            sessions.append(
                {
                    "id": session.id,
                    "title": title,
                    "lastUpdated": session.last_update_time,
                }
            )

        sessions.sort(key=lambda s: s["lastUpdated"], reverse=True)
        return {"sessions": sessions}

    async def get_session_messages(self, session_id: str, user_id: str) -> dict:
        """Get session details including parsed messages."""
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        if not session:
            return None

        merged_messages = self._build_messages(session.events)

        return {
            "id": session.id,
            "messages": merged_messages,
            "lastUpdated": session.last_update_time,
        }

    async def cancel_execution(self, session_id: str, adk_agent) -> bool:
        """Cancel an active agent execution. Returns True if cancelled."""
        execution = adk_agent._active_executions.get(session_id)
        if not execution:
            return False

        logger.info(f"Cancelling execution for session {session_id}")
        await execution.event_queue.put(None)
        await execution.cancel()

        async with adk_agent._execution_lock:
            adk_agent._active_executions.pop(session_id, None)

        return True

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session. Returns True on success."""
        await session_service.delete_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        return True

    # ── Debug helpers ────────────────────────────────────────────────────

    async def get_debug_session(self, session_id: str, user_id: str) -> dict | None:
        """Get full session details for debugging."""
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        if not session:
            return None

        events = [_serialize_event(event) for event in session.events]
        return {
            "id": session.id,
            "app_name": session.app_name,
            "user_id": session.user_id,
            "state": dict(session.state) if session.state else {},
            "last_update_time": session.last_update_time,
            "event_count": len(events),
            "events": events,
        }

    async def get_debug_events(
        self, session_id: str, user_id: str, limit: int = 50, offset: int = 0
    ) -> dict | None:
        """Get paginated events for debugging."""
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        if not session:
            return None

        total = len(session.events)
        events = [
            _serialize_event(event)
            for event in session.events[offset : offset + limit]
        ]
        return {
            "session_id": session_id,
            "total_events": total,
            "offset": offset,
            "limit": limit,
            "events": events,
        }

    async def get_debug_state(self, session_id: str, user_id: str) -> dict | None:
        """Get only session state for debugging."""
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )
        if not session:
            return None

        return {
            "session_id": session_id,
            "state": dict(session.state) if session.state else {},
        }

    async def list_debug_sessions(self, user_id: str) -> dict:
        """List sessions with minimal info for debugging."""
        response = await session_service.list_sessions(
            app_name=APP_NAME, user_id=user_id
        )

        sessions = [
            {"id": s.id, "last_update_time": s.last_update_time}
            for s in response.sessions
        ]
        sessions.sort(key=lambda s: s["last_update_time"], reverse=True)

        return {
            "user_id": user_id,
            "session_count": len(sessions),
            "sessions": sessions,
        }

    # ── Private helpers ──────────────────────────────────────────────────

    def _build_messages(self, events) -> list[dict]:
        """Parse ADK events into merged message list for frontend."""
        # Collect tool results for merging with their calls
        pending_tool_results: dict[str, str] = {}

        for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "function_response") and part.function_response:
                        fr = part.function_response
                        result_id = getattr(fr, "id", "")
                        response = fr.response if hasattr(fr, "response") else None
                        result_json = json.dumps(response) if response else "{}"
                        if result_id:
                            pending_tool_results[result_id] = result_json

        # Build messages grouped by invocation_id
        invocation_groups: dict[str, dict] = {}
        invocation_order: list[str] = []

        for event in events:
            if not (event.content and event.content.parts):
                continue

            inv_id = getattr(event, "invocation_id", None) or "unknown"
            author = getattr(event, "author", "")
            is_user_authored = author == "user"

            if inv_id not in invocation_groups:
                invocation_groups[inv_id] = {"user": None, "assistant": None}
                invocation_order.append(inv_id)

            text_parts = []
            has_displayable_content = False

            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    has_displayable_content = True
                    if getattr(part, "thought", False):
                        text_parts.append(
                            f"{THOUGHT_TAG_OPEN}{part.text}{THOUGHT_TAG_CLOSE}"
                        )
                    else:
                        text_parts.append(part.text)

                if hasattr(part, "function_call") and part.function_call:
                    has_displayable_content = True
                    fc = part.function_call
                    tool_name = getattr(fc, "name", "unknown")
                    tool_id = getattr(fc, "id", "")
                    args = fc.args if hasattr(fc, "args") and fc.args else {}
                    args_json = json.dumps(dict(args)) if args else "{}"
                    text_parts.append(
                        f"{TOOL_TAG_OPEN.format(name=tool_name, id=tool_id)}"
                        f"{args_json}{TOOL_TAG_CLOSE}"
                    )
                    if tool_id and tool_id in pending_tool_results:
                        text_parts.append(
                            f"{TOOL_RESULT_TAG_OPEN.format(id=tool_id)}"
                            f"{pending_tool_results[tool_id]}{TOOL_RESULT_TAG_CLOSE}"
                        )

            combined_text = "".join(text_parts)
            if not (combined_text and has_displayable_content):
                continue

            msg_key = "user" if is_user_authored else "assistant"
            role = "user" if is_user_authored else "model"

            if invocation_groups[inv_id][msg_key] is None:
                invocation_groups[inv_id][msg_key] = {
                    "role": role,
                    "content": combined_text,
                    "timestamp": getattr(event, "timestamp", None),
                    "invocationId": inv_id,
                }
            else:
                invocation_groups[inv_id][msg_key]["content"] += combined_text
                invocation_groups[inv_id][msg_key]["timestamp"] = getattr(
                    event, "timestamp", None
                )

        # Flatten to chronological list
        merged = []
        for inv_id in invocation_order:
            group = invocation_groups[inv_id]
            if group["user"]:
                merged.append(group["user"])
            if group["assistant"]:
                merged.append(group["assistant"])

        return merged


# Module-level singleton
session_svc = SessionService()

