"""
CopilotKit endpoint — official self-hosted auth pattern per:
https://docs.copilotkit.ai/langgraph/auth

Flow:
  Frontend: <CopilotKit properties={{ authorization: firebaseIdToken }}>
  → forwarded_props["authorization"] arrives in RunAgentInput
  → We verify token, upsert user in DB, inject user.id as mem0_user_id into state
  → agent.run() executes with real user context

Memory /api/* routes are protected separately by Depends(get_current_user).
"""
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder
from ag_ui_langgraph import LangGraphAgent
from routes.agent.graph import create_agent_graph

logger = logging.getLogger(__name__)

_PROTECTED_PREFIXES = ("/api/memories",)


async def _resolve_user_id(token: str | None) -> str | None:
    """
    Verify Firebase token → upsert user in PostgreSQL → return UUIDv7 user.id.
    Returns None if token is missing or invalid.
    """
    if not token:
        return None
    token = token.removeprefix("Bearer ").strip()
    try:
        from core.firebase import verify_id_token
        from core.database import AsyncSessionLocal
        from models.user import User
        from sqlalchemy import select
        from datetime import datetime, timezone

        claims = verify_id_token(token)
        firebase_uid = claims["uid"]

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.firebase_uid == firebase_uid)
            )
            user = result.scalar_one_or_none()

            if user is None:
                user = User(
                    firebase_uid=firebase_uid,
                    email=claims.get("email"),
                    display_name=claims.get("name"),
                    photo_url=claims.get("picture"),
                )
                db.add(user)
                logger.info("New user: %s (%s)", firebase_uid, claims.get("email"))
            else:
                user.email = claims.get("email")
                user.display_name = claims.get("name")
                user.photo_url = claims.get("picture")
                user.last_seen_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(user)
            return user.id
    except Exception as e:
        logger.warning("Auth failed: %s", e)
        return None


async def setup_copilotkit(app: FastAPI):
    """
    Register /copilotkit endpoint with Firebase auth + user injection.
    The /api/memories routes are separately protected via Depends(get_current_user).
    """
    logger.info("Setting up CopilotKit endpoint...")

    graph = await create_agent_graph()
    agent = LangGraphAgent(
        name="default",
        description="MCP-powered AI assistant with real-time state tracking",
        graph=graph,
    )
    encoder = EventEncoder()

    # ── Custom /copilotkit endpoint ─────────────────────────────────────
    @app.post("/copilotkit")
    async def copilotkit_endpoint(input_data: RunAgentInput, request: Request):
        """
        Accepts CopilotKit AG-UI protocol.
        Extracts Firebase token from forwarded_props.authorization,
        verifies it, and injects mem0_user_id (UUIDv7) into state.
        """
        accept = request.headers.get("accept")
        enc = EventEncoder(accept=accept)

        forwarded = input_data.forwarded_props or {}
        raw_token = forwarded.get("authorization") or forwarded.get("Authorization")

        if not raw_token:
            raw_token = request.headers.get("Authorization", "")

        user_id = await _resolve_user_id(raw_token)

        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized — valid Firebase token required"},
            )

        existing_state = input_data.state or {}
        patched_state = {**existing_state, "mem0_user_id": user_id}
        patched_input = input_data.copy(update={"state": patched_state})

        logger.debug("CopilotKit request: user_id=%s thread=%s", user_id, input_data.thread_id)

        async def event_generator():
            async for event in agent.run(patched_input):
                yield enc.encode(event)

        return StreamingResponse(
            event_generator(),
            media_type=enc.get_content_type(),
        )

    @app.get("/copilotkit/health")
    def copilotkit_health():
        return {"status": "ok", "agent": "default"}

    logger.info("CopilotKit ready at POST /copilotkit")
