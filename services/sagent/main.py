"""FastAPI server exposing the agent via AG-UI protocol.

This is the application entry point. It:
1. Configures logging and patches
2. Creates the FastAPI app with middleware
3. Sets up the ADK agent with AG-UI adapter
4. Registers all route modules

All business logic lives in services/. All route handlers live in api/routes/.

Usage:
    uv run uvicorn main:app --reload --port 8000
    # or
    python main.py
"""

# Configure logging before any ADK imports
from logging_config import configure_logging

configure_logging()

# Apply monkey patches before importing patched modules
import patches  # noqa: F401 - side effect import applies thought tag patch

import logging
from contextlib import asynccontextmanager

from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent import root_agent
from agents.mcp_manager import pull_stdio_mcp_images
from api.routes import register_routes
from config.settings import settings
from core.dependencies import (
    artifact_service,
    extract_user_id,
    session_service,
    set_adk_agent,
)

logger = logging.getLogger(__name__)


# ── Startup / Shutdown lifecycle ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks before accepting requests.

    On every startup sagent will:
    1. Scan all mcp_agents/*/mcp.json for stdio+docker servers
    2. Pull any Docker images that are not yet available locally
    3. Then yield — app becomes ready to accept requests
    """
    await pull_stdio_mcp_images()
    yield
    # Shutdown cleanup (if needed in future)


# ── Create FastAPI application ───────────────────────────────────────────

app = FastAPI(
    title="Agent API",
    description="Enterprise knowledge assistant powered by ADK and AG-UI",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ADK Agent + AG-UI Adapter ────────────────────────────────────────────

adk_agent = ADKAgent(
    adk_agent=root_agent,
    user_id_extractor=extract_user_id,
    session_service=session_service,
    artifact_service=artifact_service,
    session_timeout_seconds=315360000,  # 10 years - effectively never expire
)

# Register in dependencies so route handlers can access it
set_adk_agent(adk_agent)

# Register the AG-UI endpoint at root path
add_adk_fastapi_endpoint(app, adk_agent, path="/", extract_headers=["x-user-id", "x-enabled-agents"])

# ── Routes ───────────────────────────────────────────────────────────────

register_routes(app)

# ── Development server ───────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    print(f"Starting agent server on port {settings.PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
