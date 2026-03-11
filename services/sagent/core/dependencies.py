"""Shared application dependencies — singleton services.

Provides session service, artifact service, and ADK agent instances
used by route handlers via dependency injection.

Usage:
    from core.dependencies import session_service, artifact_service, get_adk_agent
"""

import logging
from typing import TYPE_CHECKING

from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.adk.sessions import DatabaseSessionService

from config.settings import settings

if TYPE_CHECKING:
    from ag_ui_adk import ADKAgent

logger = logging.getLogger(__name__)


# ── Session Service ──────────────────────────────────────────────────────

def create_session_service() -> DatabaseSessionService:
    """Create session service with PostgreSQL backend."""
    logger.info("Using PostgreSQL for session storage")
    return DatabaseSessionService(db_url=settings.DATABASE_URL)


session_service = create_session_service()


# ── Artifact Service ─────────────────────────────────────────────────────

def create_artifact_service():
    """Create artifact service based on environment.

    Production: GCS bucket via Vertex AI service account.
    Development with MinIO: S3-compatible local storage.
    Development without MinIO: In-memory (ephemeral).
    """
    if settings.is_production:
        logger.info(f"Using GcsArtifactService with bucket: {settings.ARTIFACT_BUCKET}")
        return GcsArtifactService(bucket_name=settings.ARTIFACT_BUCKET)

    if settings.MINIO_ENDPOINT:
        from core.minio_artifact import MinioArtifactService

        logger.info(
            f"Using MinioArtifactService: {settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}"
        )
        return MinioArtifactService(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            bucket=settings.MINIO_BUCKET,
            secure=settings.MINIO_SECURE,
        )

    logger.info("Using InMemoryArtifactService for development")
    return InMemoryArtifactService()


artifact_service = create_artifact_service()


# ── ADK Agent (set during app startup in main.py) ────────────────────────

_adk_agent: "ADKAgent | None" = None


def set_adk_agent(agent: "ADKAgent") -> None:
    """Register the ADK agent instance (called once from main.py)."""
    global _adk_agent
    _adk_agent = agent


def get_adk_agent() -> "ADKAgent":
    """Get the ADK agent instance. Raises if not yet initialised."""
    if _adk_agent is None:
        raise RuntimeError("ADK agent not initialised — call set_adk_agent() first")
    return _adk_agent


# ── User ID Extraction ───────────────────────────────────────────────────

def extract_user_id(input_data) -> str:
    """Extract user ID from AG-UI state headers.

    The x-user-id header is:
    1. Set by frontend from Firebase Auth session (user email)
    2. Forwarded by CopilotKit runtime to ADK backend
    3. Extracted into state.headers.user_id by add_adk_fastapi_endpoint
    """
    if isinstance(input_data.state, dict):
        headers = input_data.state.get("headers", {})
        if isinstance(headers, dict):
            user_id = headers.get("user_id")
            if user_id:
                user_id = user_id.strip()
                return user_id

    available_headers = {}
    if isinstance(input_data.state, dict):
        available_headers = input_data.state.get("headers", {})

    logger.error(
        f"[extract_user_id] Missing user_id in state. "
        f"thread_id={input_data.thread_id}, "
        f"available_headers={list(available_headers.keys()) if available_headers else 'none'}. "
        "Check that Firebase Auth session is valid and CopilotKit is forwarding x-user-id header."
    )
    raise ValueError(
        "Authentication required: x-user-id header missing. "
        "Ensure user is logged in and page is fully loaded before using chat."
    )

