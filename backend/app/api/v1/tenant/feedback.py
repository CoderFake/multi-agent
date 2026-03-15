"""
Feedback API — submit platform feedback (any authenticated user).
NOT tenant-scoped. Feedback is for the system/platform.
Admin list + status update requires superuser.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_current_user, require_superuser
from app.common.types import CurrentUser
from app.schemas.feedback import FeedbackStatusUpdate
from app.services.feedback import feedback_svc
from app.services.audit import audit_svc
from app.utils.request_utils import get_request_origin

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", status_code=201)
async def submit_feedback(
    request: Request,
    category: str = Form(...),
    message: str = Form(...),
    images: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(get_current_user),
):
    """Submit platform feedback with optional image attachments (any authenticated user)."""
    feedback = await feedback_svc.create(
        db, user.user_id, None, category, message, images or None,
    )
    await audit_svc.log_action(
        db, user.user_id, "submit", "feedback", str(feedback.id),
        new_values={"category": category},
    )
    return {
        "id": str(feedback.id),
        "category": feedback.category,
        "message": feedback.message,
        "attachments": feedback.attachments,
        "status": feedback.status,
    }


@router.get("")
async def list_feedback(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_superuser),
):
    """List all feedback (superuser/admin only)."""
    items, total = await feedback_svc.list_all_feedback(
        db, status, page, page_size,
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.put("/{feedback_id}/status")
async def update_feedback_status(
    feedback_id: str,
    data: FeedbackStatusUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_superuser),
):
    """Update feedback status (superuser/admin only)."""
    fb = await feedback_svc.update_status(db, feedback_id, data.status)
    await audit_svc.log_action(
        db, user.user_id, "update_status", "feedback", feedback_id,
        new_values={"status": data.status},
    )
    return {"id": str(fb.id), "status": fb.status}
