"""Route registration for the retrieval microservice.

Usage:
    from app.routes import register_routes
    register_routes(app)
"""

from fastapi import FastAPI

from app.routes.files import router as files_router
from app.routes.health import router as health_router
from app.routes.index import router as index_router
from app.routes.search import router as search_router


def register_routes(app: FastAPI) -> None:
    """Register all API routers on the FastAPI application."""
    app.include_router(health_router, tags=["Health"])
    app.include_router(search_router, tags=["Search"])
    app.include_router(index_router, tags=["Index"])
    app.include_router(files_router, tags=["Files"])

