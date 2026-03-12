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
