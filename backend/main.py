"""
CMS Backend — FastAPI application.
Root uvicorn entrypoint.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.core.database import db_manager, redis_manager
from app.core.middleware import setup_middlewares
from app.core.exceptions import CmsException, cms_exception_handler
from app.utils.logging import setup_logging, get_logger
from app.common.enums import Environment
from app.api.v1.router import api_router

setup_logging(debug=settings.DEBUG)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager — startup and shutdown."""
    logger.info("Starting CMS Backend...")

    try:
        await db_manager.connect()
        logger.info("Database connection established")

        await redis_manager.connect()
        logger.info("Redis connection established")

        app.state.redis = redis_manager.get_redis()
        app.state.db_session = db_manager.get_session

        from app.init_db import seed_content_types_and_permissions, seed_default_groups, seed_superuser
        async with db_manager.session() as db:
            perm_map = await seed_content_types_and_permissions(db)
            await seed_default_groups(db, perm_map)
            await seed_superuser(db)

        logger.info("CMS Backend started successfully")

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

    yield

    logger.info("Shutting down CMS Backend...")
    try:
        await redis_manager.disconnect()
        logger.info("Redis connection closed")

        await db_manager.disconnect()
        logger.info("Database connection closed")

        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# ── App factory ──────────────────────────────────────────────────────────

DEBUG = settings.ENVIRONMENT == Environment.DEVELOPMENT.value or settings.DEBUG

if settings.ENVIRONMENT in [Environment.PRODUCTION.value, Environment.STAGING.value]:
    docs_url = None
    redoc_url = None
    openapi_url = None
else:
    docs_url = "/docs"
    redoc_url = "/redoc"
    openapi_url = "/openapi.json"

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="CMS Backend for Multi-Agent Platform",
    lifespan=lifespan,
    debug=DEBUG,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

# Register exception handler
app.add_exception_handler(CmsException, cms_exception_handler)

# Setup middlewares
setup_middlewares(app)


# ── Routes ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    try:
        redis = redis_manager.get_redis()
        await redis.ping()

        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "service": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "database": "connected",
                "redis": "connected",
            },
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "error": str(e),
            },
        )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ── Uvicorn entrypoint ───────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn_config = {
        "app": "main:app",
        "host": "0.0.0.0",
        "port": settings.CMS_PORT,
    }

    if settings.ENVIRONMENT == Environment.DEVELOPMENT.value:
        uvicorn_config.update({
            "reload": True,
            "log_level": "debug",
        })
        logger.info("Starting in DEVELOPMENT mode (reload=True)")
    else:
        uvicorn_config.update({
            "reload": False,
            "log_level": "info",
        })
        logger.info(f"Starting in {settings.ENVIRONMENT.upper()} mode")

    uvicorn.run(**uvicorn_config)
