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
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder
from ag_ui_langgraph import LangGraphAgent
from routes.agent.graph import create_agent_graph
from core.database import get_db
from core.dependencies import sync_user_from_claims

logger = logging.getLogger(__name__)


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
    async def copilotkit_endpoint(
        input_data: RunAgentInput,
        request: Request,
        db: AsyncSession = Depends(get_db),
    ):
        """
        Accepts CopilotKit AG-UI protocol.
        Extracts Firebase token from forwarded_props.authorization,
        verifies it, and injects mem0_user_id (UUIDv7) into state.
        """
        accept = request.headers.get("accept")
        enc = EventEncoder(accept=accept)

        forwarded = input_data.forwarded_props or {}
        raw_token = forwarded.get("authorization") or forwarded.get("Authorization") or ""
        if not raw_token:
            raw_token = request.headers.get("Authorization", "")
        raw_token = raw_token.removeprefix("Bearer ").strip()

        user_id = None
        if raw_token:
            try:
                from core.firebase import verify_id_token
                claims = verify_id_token(raw_token)
                user = await sync_user_from_claims(db, claims["uid"], claims)
                await db.flush()
                user_id = user.id
            except Exception as e:
                logger.warning("Auth failed: %s", e)

        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized — valid Firebase token required"},
            )

        research_mode = bool(forwarded.get("researchMode", False))

        existing_state = input_data.state or {}
        patched_state = {**existing_state, "mem0_user_id": user_id, "research_mode": research_mode}
        patched_input = input_data.copy(update={"state": patched_state})

        logger.debug("CopilotKit request: user_id=%s thread=%s research_mode=%s", user_id, input_data.thread_id, research_mode)

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
