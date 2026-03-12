"""
Application middlewares: request logging, tenant resolution, error handling, CORS.
"""
import time
import uuid
import re
from typing import Callable, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.common.enums import Environment
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs HTTP requests/responses with timing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()
        logger.info(
            f"Request started | ID: {request_id} | "
            f"Method: {request.method} | Path: {request.url.path}"
        )

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"

            logger.info(
                f"Request completed | ID: {request_id} | "
                f"Status: {response.status_code} | "
                f"Time: {process_time:.4f}s"
            )
            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed | ID: {request_id} | "
                f"Error: {str(e)} | Time: {process_time:.4f}s",
                exc_info=True,
            )
            raise


class TenantResolverMiddleware(BaseHTTPMiddleware):
    """
    Resolves tenant from URL path or subdomain.

    Dev:       /t/{tenant_id}/...  → request.state.org_id
    Stg/Prod:  {slug}.domain.com   → request.state.org_slug
    """

    # Regex to match /t/{uuid}/... pattern
    TENANT_PATH_PATTERN = re.compile(r"^/t/([a-f0-9\-]{36})/")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request.state.org_id = None
        request.state.org_slug = None

        path = request.url.path

        # Skip tenant resolution for non-tenant routes
        if any(path.startswith(p) for p in ["/health", "/docs", "/redoc", "/openapi.json", "/auth", "/system"]):
            return await call_next(request)

        if settings.ENVIRONMENT == Environment.DEVELOPMENT.value:
            # Path-based: /t/{tenant_id}/...
            match = self.TENANT_PATH_PATTERN.match(path)
            if match:
                request.state.org_id = match.group(1)
        else:
            # Subdomain-based: {slug}.domain.com
            host = request.headers.get("host", "")
            parts = host.split(".")
            if len(parts) >= 3:
                request.state.org_slug = parts[0]

        return await call_next(request)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling for unhandled exceptions."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(
                f"Unhandled exception | Request ID: {request_id} | "
                f"Path: {request.url.path} | Error: {str(e)}",
                exc_info=True,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error_code": "INTERNAL_ERROR",
                    "detail": "Internal server error",
                    "request_id": request_id,
                },
            )


def setup_cors(app) -> None:
    """Setup CORS middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )


def setup_middlewares(app) -> None:
    """
    Register all application middlewares.
    Order matters: last added is executed first.
    """
    app.add_middleware(ErrorHandlingMiddleware)
    setup_cors(app)
    app.add_middleware(TenantResolverMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
