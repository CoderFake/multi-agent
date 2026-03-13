"""
Feedback service — submit with S3 image upload, list, update status.
Feedback is platform-level (not org-scoped).
"""
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from app.core.exceptions import CmsException
from app.common.constants import (
    ErrorCode, FeedbackConstants, FeedbackCategory, FeedbackStatus,
    NotificationType, NotificationCode,
)
from app.models.feedback import CmsFeedback
from app.models.user import CmsUser
from app.utils.storage import upload_file, get_public_url, generate_path
from app.utils.logging import get_logger
from app.config.settings import settings

logger = get_logger(__name__)


class FeedbackService:
    """Feedback CRUD with S3 image upload. Platform-level (no org scope)."""

    async def create(
        self, db: AsyncSession,
        user_id: str, org_id: Optional[str],
        category: str, message: str,
        files: Optional[list[UploadFile]] = None,
    ) -> CmsFeedback:
        """Create feedback with optional image attachments uploaded to S3."""
        attachment_paths = []

        if files:
            if len(files) > FeedbackConstants.MAX_ATTACHMENTS:
                raise CmsException(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    detail=f"Maximum {FeedbackConstants.MAX_ATTACHMENTS} attachments allowed",
                    status_code=400,
                )

            for file in files:
                if file.content_type not in FeedbackConstants.ALLOWED_IMAGE_TYPES:
                    raise CmsException(
                        error_code=ErrorCode.VALIDATION_ERROR,
                        detail=f"Invalid file type: {file.content_type}",
                        status_code=400,
                    )

            # Upload all files
            for file in files:
                path = generate_path(f"feedback/{user_id}", file.filename or "image.png")
                await upload_file(file, path, bucket=settings.BUCKET_SYSTEM)
                attachment_paths.append(path)

        feedback = CmsFeedback(
            user_id=user_id,
            org_id=org_id,
            category=category,
            message=message,
            attachments=attachment_paths if attachment_paths else None,
            status=FeedbackStatus.NEW,
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        logger.info(f"Feedback created: {category} by user {user_id} ({len(attachment_paths)} attachments)")

        # Notify all superusers about new feedback
        from app.services.notification import notification_svc
        await notification_svc.notify_superusers(
            db,
            NotificationType.FEEDBACK_SUBMITTED,
            NotificationCode.FEEDBACK_SUBMITTED,
            NotificationCode.FEEDBACK_SUBMITTED_DESC,
            {"category": category, "user_id": user_id, "feedback_id": str(feedback.id)},
        )

        return feedback

    async def list_all_feedback(
        self, db: AsyncSession,
        status: Optional[str] = None,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """List all platform feedback (superuser view) with user info and public URLs."""
        query = (
            select(CmsFeedback, CmsUser.email, CmsUser.full_name)
            .outerjoin(CmsUser, CmsFeedback.user_id == CmsUser.id)
        )
        count_q = select(func.count(CmsFeedback.id))

        if status:
            query = query.where(CmsFeedback.status == status)
            count_q = count_q.where(CmsFeedback.status == status)

        total = (await db.execute(count_q)).scalar() or 0

        query = (
            query.order_by(CmsFeedback.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)

        items = []
        for fb, email, full_name in result.all():
            public_attachments = None
            if fb.attachments:
                public_attachments = [
                    get_public_url(p, bucket=settings.BUCKET_SYSTEM) for p in fb.attachments
                ]

            items.append({
                "id": str(fb.id),
                "user_id": str(fb.user_id),
                "user_email": email,
                "user_full_name": full_name,
                "category": fb.category,
                "message": fb.message,
                "attachments": public_attachments,
                "status": fb.status,
                "created_at": fb.created_at,
            })

        return items, total

    async def update_status(
        self, db: AsyncSession, feedback_id: str, status: str,
    ) -> CmsFeedback:
        """Update feedback status (admin action)."""
        result = await db.execute(
            select(CmsFeedback).where(CmsFeedback.id == feedback_id)
        )
        feedback = result.scalar_one_or_none()
        if not feedback:
            raise CmsException(
                error_code=ErrorCode.NOT_FOUND,
                detail="Feedback not found",
                status_code=404,
            )
        feedback.status = status
        await db.commit()
        await db.refresh(feedback)
        return feedback


# Singleton
feedback_svc = FeedbackService()
