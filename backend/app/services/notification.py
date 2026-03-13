"""
Notification service — create, list, mark read, count unread.
Uses i18n codes (title_code, message_code) — frontend resolves text.
No caching (real-time data).
"""
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import CmsNotification
from app.models.user import CmsUser
from app.utils.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Notification CRUD — i18n code based."""

    async def create(
        self, db: AsyncSession,
        user_id: str, org_id: Optional[str],
        type: str, title_code: str,
        message_code: Optional[str] = None,
        data: Optional[dict] = None,
    ) -> CmsNotification:
        """Create a notification for a user using i18n codes."""
        notification = CmsNotification(
            user_id=user_id,
            org_id=org_id,
            type=type,
            title_code=title_code,
            message_code=message_code,
            data=data,
            is_read=False,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        logger.info(f"Notification [{type}] for user {user_id}")
        return notification

    async def create_bulk(
        self, db: AsyncSession,
        user_ids: list[str], org_id: Optional[str],
        type: str, title_code: str,
        message_code: Optional[str] = None,
        data: Optional[dict] = None,
    ) -> None:
        """Create notification for multiple users."""
        for uid in user_ids:
            db.add(CmsNotification(
                user_id=uid, org_id=org_id,
                type=type, title_code=title_code,
                message_code=message_code, data=data, is_read=False,
            ))
        await db.commit()
        logger.info(f"Bulk notification [{type}] for {len(user_ids)} users")

    async def notify_superusers(
        self, db: AsyncSession,
        type: str, title_code: str,
        message_code: Optional[str] = None,
        data: Optional[dict] = None,
        org_id: Optional[str] = None,
    ) -> None:
        """Notify all superusers (e.g. new feedback submitted)."""
        result = await db.execute(
            select(CmsUser.id).where(
                CmsUser.is_superuser.is_(True),
                CmsUser.is_active.is_(True),
                CmsUser.deleted_at.is_(None),
            )
        )
        su_ids = [str(uid) for (uid,) in result.all()]
        if su_ids:
            await self.create_bulk(db, su_ids, org_id, type, title_code, message_code, data)

    async def list_notifications(
        self, db: AsyncSession,
        user_id: str, org_id: str,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[dict], int, int]:
        """
        List notifications for a user (unread first, then by date).
        Returns (items, total, unread_count).
        """
        base_where = [
            CmsNotification.user_id == user_id,
            (CmsNotification.org_id == org_id) | (CmsNotification.org_id.is_(None)),
        ]

        # Total
        total = (await db.execute(
            select(func.count(CmsNotification.id)).where(*base_where)
        )).scalar() or 0

        # Unread
        unread_count = (await db.execute(
            select(func.count(CmsNotification.id)).where(
                *base_where, CmsNotification.is_read.is_(False),
            )
        )).scalar() or 0

        # Paginated — unread first, newest first
        query = (
            select(CmsNotification)
            .where(*base_where)
            .order_by(CmsNotification.is_read.asc(), CmsNotification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(query)
        items = [
            {
                "id": str(n.id),
                "type": n.type,
                "title_code": n.title_code,
                "message_code": n.message_code,
                "data": n.data,
                "is_read": n.is_read,
                "created_at": n.created_at,
            }
            for n in result.scalars().all()
        ]

        return items, total, unread_count

    async def count_unread(self, db: AsyncSession, user_id: str, org_id: str) -> int:
        """Count unread notifications (org + system-level)."""
        result = await db.execute(
            select(func.count(CmsNotification.id)).where(
                CmsNotification.user_id == user_id,
                (CmsNotification.org_id == org_id) | (CmsNotification.org_id.is_(None)),
                CmsNotification.is_read.is_(False),
            )
        )
        return result.scalar() or 0

    async def mark_read(self, db: AsyncSession, notification_id: str, user_id: str) -> bool:
        """Mark a single notification as read."""
        result = await db.execute(
            update(CmsNotification)
            .where(CmsNotification.id == notification_id, CmsNotification.user_id == user_id)
            .values(is_read=True)
        )
        await db.commit()
        return result.rowcount > 0

    async def mark_all_read(self, db: AsyncSession, user_id: str, org_id: str) -> int:
        """Mark all unread notifications as read. Returns count updated."""
        result = await db.execute(
            update(CmsNotification)
            .where(
                CmsNotification.user_id == user_id,
                (CmsNotification.org_id == org_id) | (CmsNotification.org_id.is_(None)),
                CmsNotification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        await db.commit()
        return result.rowcount


# Singleton
notification_svc = NotificationService()
