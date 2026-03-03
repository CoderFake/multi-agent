"""
file-service main entrypoint.
Starts FastAPI + async gRPC server concurrently.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.core.database import init_db
from app.services.grpc import start_grpc_server
from app.utils.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# ── gRPC server handle (set during lifespan) ──
_grpc_server = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _grpc_server
    await init_db()

    _grpc_server = await start_grpc_server()
    logger.info("gRPC server started on %s:%s", settings.grpc_host, settings.grpc_port)

    logger.info("file-service ready")
    yield

    if _grpc_server:
        await _grpc_server.stop(grace=5)
    logger.info("file-service shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="file-service",
        description="Document processing & PageIndex service",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.v1.document import router as doc_router
    app.include_router(doc_router, prefix="/api/v1/documents", tags=["documents"])

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "file-service"}

    return app


app = create_app()


async def main():
    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
