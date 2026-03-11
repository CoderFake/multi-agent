"""Retrieval microservice — FastAPI application entry point.

This is the app entry point. It:
1. Creates the FastAPI app with OpenAPI metadata
2. Manages Milvus connection and RabbitMQ consumer lifecycle
3. Registers all route modules

All business logic lives in app/services/. All route handlers live in app/routes/.

Usage:
    uvicorn main:app --host 0.0.0.0 --port 8001
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.milvus import close_milvus, get_milvus_client
from app.routes import register_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Startup: verify Milvus connection
    try:
        get_milvus_client()
        logger.info("Milvus connection verified")
    except Exception as e:
        logger.error(f"Failed to connect to Milvus: {e}")

    # Start RabbitMQ consumers in background
    try:
        from app.worker import start_consumers

        start_consumers()
        logger.info("RabbitMQ consumers started")
    except Exception as e:
        logger.warning(f"RabbitMQ consumers not started: {e}")

    yield

    # Shutdown
    close_milvus()
    logger.info("Retrieval service shut down")


app = FastAPI(
    title="Retrieval Microservice",
    description=(
        "Vector search and document indexing service backed by Milvus. "
        "Provides semantic search, document ingestion, and file listing APIs. "
        "Communicates with sagent via RabbitMQ queues."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

register_routes(app)

