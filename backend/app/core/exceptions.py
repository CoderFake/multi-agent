"""
Custom exceptions and global exception handler for the CMS backend.
All HTTPException responses include error_code for frontend i18n mapping.
"""
from fastapi import Request
from fastapi.responses import JSONResponse

from app.utils.logging import get_logger

logger = get_logger(__name__)


class CmsException(Exception):
    """
    Custom CMS exception with structured error response.

    Usage:
        raise CmsException(
            error_code="AUTH_INVALID_CREDENTIALS",
            status_code=401,
            detail="Invalid email or password"
        )
    """

    def __init__(self, error_code: str, status_code: int = 400, detail: str = ""):
        self.error_code = error_code
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def cms_exception_handler(request: Request, exc: CmsException) -> JSONResponse:
    """
    Global exception handler for CmsException.
    Returns JSON: {error_code, detail, status_code}.
    """
    logger.warning(
        f"CmsException | code={exc.error_code} | status={exc.status_code} | "
        f"detail={exc.detail} | path={request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )
