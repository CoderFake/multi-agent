"""
Tenant Audit Log API — read audit logs with filters.
Router = thin delegation only. All logic in tenant_audit_svc.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_permission
from app.common.types import CurrentUser
from app.services.tenant_audit import tenant_audit_svc

router = APIRouter(prefix="/audit-logs", tags=["tenant-audit"])


@router.get("")
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("audit_log.view")),
):
    """List audit logs for the current org."""
    items, total = await tenant_audit_svc.list_logs(
        db, user.org_id, action, resource_type, user_id, page, page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}
