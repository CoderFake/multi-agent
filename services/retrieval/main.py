"""Retrieval microservice — FastAPI application entry point.

This is the app entry point. It:
1. Creates the FastAPI app with OpenAPI metadata
2. Manages Milvus + Redis connection lifecycle
3. Starts Redis indexing consumer + RabbitMQ RAG consumer
4. Registers all route modules

Usage:
    uvicorn main:app --host 0.0.0.0 --port 8001
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.milvus import connect_milvus, disconnect_milvus
from app.worker import start_indexing_consumer, start_rabbitmq_consumer
from app.core.redis import close_redis, get_redis
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
        connect_milvus()
        logger.info("Milvus connection verified")
    except Exception as e:
        logger.error("Failed to connect to Milvus: %s", e)

    # Startup: verify Redis connection
    try:
        get_redis()
        logger.info("Redis connection verified")
    except Exception as e:
        logger.error("Failed to connect to Redis: %s", e)

    try:
        start_indexing_consumer()
        logger.info("Redis indexing consumer started")

        start_rabbitmq_consumer()
        logger.info("RabbitMQ RAG consumer started")
    except Exception as e:
        logger.warning("Consumers not started: %s", e)

    yield

    disconnect_milvus()
    close_redis()
    logger.info("Retrieval service shut down")


app = FastAPI(
    title="Retrieval Microservice",
    description=(
        "Vector search and document indexing service backed by Milvus. "
        "Provides semantic search, document ingestion, and file listing APIs. "
        "Communicates via Redis queue for indexing and RabbitMQ for RAG requests."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

register_routes(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
