"""
Tenant audit log service — list audit logs with filters and pagination.
"""
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import CmsAuditLog
from app.models.user import CmsUser
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TenantAuditService:
    """Audit log listing within an org."""

    async def list_logs(
        self, db: AsyncSession, org_id: str,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        user_id: Optional[str] = None,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """List audit logs for an org with filters and pagination."""
        # Base query
        query = (
            select(CmsAuditLog, CmsUser.email, CmsUser.full_name)
            .outerjoin(CmsUser, CmsAuditLog.user_id == CmsUser.id)
            .where(CmsAuditLog.org_id == org_id)
        )

        # Filters
        if action:
            query = query.where(CmsAuditLog.action == action)
        if resource_type:
            query = query.where(CmsAuditLog.resource_type == resource_type)
        if user_id:
            query = query.where(CmsAuditLog.user_id == user_id)

        # Count
        count_q = select(func.count(CmsAuditLog.id)).where(CmsAuditLog.org_id == org_id)
        if action:
            count_q = count_q.where(CmsAuditLog.action == action)
        if resource_type:
            count_q = count_q.where(CmsAuditLog.resource_type == resource_type)
        if user_id:
            count_q = count_q.where(CmsAuditLog.user_id == user_id)
        total = (await db.execute(count_q)).scalar() or 0

        # Paginate
        query = query.order_by(CmsAuditLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)

        items = []
        for log, email, full_name in result.all():
            items.append({
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "user_email": email,
                "user_full_name": full_name,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": str(log.resource_id) if log.resource_id else None,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": log.ip_address,
                "created_at": log.created_at,
            })

        return items, total


# Singleton
tenant_audit_svc = TenantAuditService()
