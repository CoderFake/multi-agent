"""
Tenant Notifications API — list, count unread, mark read.
Router = thin delegation only. All logic in notification_svc.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_org_membership
from app.common.types import CurrentUser
from app.services.notification import notification_svc

router = APIRouter(prefix="/notifications", tags=["tenant-notifications"])


@router.get("")
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_org_membership),
):
    """List notifications for current user (unread first)."""
    items, total, unread_count = await notification_svc.list_notifications(
        db, user.user_id, user.org_id, page, page_size,
    )
    return {"items": items, "total": total, "unread_count": unread_count}


@router.get("/count")
async def count_unread(
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_org_membership),
):
    """Get unread notification count."""
    count = await notification_svc.count_unread(db, user.user_id, user.org_id)
    return {"unread_count": count}


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_org_membership),
):
    """Mark a single notification as read."""
    success = await notification_svc.mark_read(db, notification_id, user.user_id)
    return {"success": success}


@router.put("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_org_membership),
):
    """Mark all notifications as read."""
    count = await notification_svc.mark_all_read(db, user.user_id, user.org_id)
    return {"marked_count": count}
