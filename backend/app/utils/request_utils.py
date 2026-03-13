"""
HTTP request utilities.
"""
from fastapi import Request
from typing import Optional


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    Checks X-Forwarded-For header first (for reverse proxy),
    then falls back to direct client host.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address string
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For: client, proxy1, proxy2
        return forwarded_for.split(",")[0].strip()

    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip()

    return request.client.host if request.client else "unknown"


def get_request_origin(request: Request) -> Optional[str]:
    """
    Get the Origin header from request.

    Args:
        request: FastAPI request object

    Returns:
        Origin string or None
    """
    return request.headers.get("origin")


def build_org_frontend_url(subdomain: str | None = None) -> str:
    """
    Build the frontend URL for an org.

    Production (BASE_DOMAIN set):
        https://{subdomain}.{BASE_DOMAIN}
    Local dev (BASE_DOMAIN empty):
        FRONTEND_URL (e.g. http://localhost:3000)

    Args:
        subdomain: org subdomain for production URLs

    Returns:
        Frontend base URL (no trailing slash)
    """
    from app.config.settings import settings

    if settings.BASE_DOMAIN and subdomain:
        # Production — subdomain-based routing
        return f"https://{subdomain}.{settings.BASE_DOMAIN}"
    else:
        # Local dev — single frontend instance
        return settings.FRONTEND_URL.rstrip("/")
