"""Title generation and retrieval service for chat sessions.

Handles automatic title generation using the model configured in settings.
Titles are stored in ADK's session.state['title'] and retrieved by querying
ADK's sessions table directly (single source of truth).

The title prompt template lives in instructions/prompts/titles.yml (user: key).
"""

import logging

from google import genai
from sqlalchemy import func

from config.settings import settings
from core.database import get_session
from instructions import load_user_prompt
from models.adk_session import AdkSession
from utils.title_blocklist import is_generic_title

logger = logging.getLogger(__name__)

# ADK app name (must match root_agent.name)
ADK_APP_NAME = "root_agent"


def get_titles_bulk(session_ids: list[str]) -> dict[str, str]:
    """Retrieve titles for multiple sessions by querying ADK's sessions table.

    Queries the JSONB state column directly from ADK's sessions table.
    Returns 'New conversation' for sessions without a title.

    Args:
        session_ids: List of session IDs to fetch titles for.

    Returns:
        Dictionary mapping session_id to title string.
    """
    if not session_ids:
        return {}

    session = get_session()
    try:
        rows = (
            session.query(
                AdkSession.id,
                func.coalesce(
                    AdkSession.state["title"].astext,
                    "New conversation",
                ).label("title"),
            )
            .filter(
                AdkSession.app_name == ADK_APP_NAME,
                AdkSession.id.in_(session_ids),
            )
            .all()
        )
        return {row.id: row.title for row in rows}
    finally:
        session.close()


_TITLE_PROMPT: str | None = None


def _get_title_prompt() -> str:
    """Lazy-load title prompt from YAML (cached after first call)."""
    global _TITLE_PROMPT
    if _TITLE_PROMPT is None:
        _TITLE_PROMPT = load_user_prompt("titles")
    return _TITLE_PROMPT


async def generate_title(events: list) -> str:
    """Generate a short title from conversation events using Gemini Flash-Lite.

    Args:
        events: List of ADK Event objects containing the conversation.

    Returns:
        A concise title string (2-3 words, max 50 chars).
    """
    # Extract conversation text from events
    conversation_parts = []
    for event in events:
        if event.content and event.content.parts:
            role = event.content.role
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    # Truncate each message to 300 chars for more context
                    text_content = part.text[:300]
                    conversation_parts.append(f"{role}: {text_content}")
                    break  # Only first text part per event

    conversation = "\n".join(conversation_parts)

    logger.debug(f"Title generation input:\n{conversation}")

    client = genai.Client(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
    )

    # Try up to 2 times if we get a generic title
    for attempt in range(2):
        response = await client.aio.models.generate_content(
            model=settings.MODEL_TITLE,
            contents=_get_title_prompt().format(conversation=conversation),
        )

        # Clean up and cap the title
        title = response.text.strip()
        title = title.strip("\"'*_`#")  # Remove quotes and markdown formatting
        title = title[:50]  # Cap at 50 chars for safety

        logger.debug(f"Title generation attempt {attempt + 1}: '{title}'")

        if not is_generic_title(title):
            return title

        logger.warning(
            f"Generic title detected: '{title}', retrying with stronger prompt"
        )

    # If still generic after retries, try to extract something from the user's first message
    if conversation_parts:
        first_user_msg = next(
            (p for p in conversation_parts if p.startswith("user:")), None
        )
        if first_user_msg:
            # Take first few words of user's message as fallback
            words = first_user_msg.replace("user:", "").strip().split()[:5]
            fallback = " ".join(words).title()
            if len(fallback) > 3:
                logger.info(f"Using fallback title from user message: '{fallback}'")
                return fallback[:50]

    # Last resort - return the generated title even if generic
    return title
