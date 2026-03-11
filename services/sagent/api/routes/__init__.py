"""Route registration — include all routers here.

Usage:
    from api.routes import register_routes
    register_routes(app)
"""

from fastapi import FastAPI

from api.routes.debug import router as debug_router
from api.routes.events import router as events_router
from api.routes.health import router as health_router
from api.routes.agents import router as agents_router
from api.routes.internal import router as internal_router
from api.routes.sessions import router as sessions_router
from api.routes.upload import router as upload_router
from api.routes.tools import router as tools_router


def register_routes(app: FastAPI) -> None:
    """Register all API routers on the FastAPI application."""
    app.include_router(health_router)
    app.include_router(agents_router)
    app.include_router(upload_router)
    app.include_router(events_router)
    app.include_router(sessions_router)
    app.include_router(internal_router)
    app.include_router(debug_router)
    app.include_router(tools_router)

