"""
Audit service — log actions for audit trail.
"""
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import CmsAuditLog
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    """Audit logging service."""

    async def log_action(
        self,
        db: AsyncSession,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        org_id: Optional[str] = None,
        old_values: Optional[dict[str, Any]] = None,
        new_values: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> CmsAuditLog:
        """Create an audit log entry."""
        log = CmsAuditLog(
            user_id=user_id,
            org_id=org_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
        )
        db.add(log)
        await db.flush()
        return log

    async def list_logs(
        self,
        db: AsyncSession,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CmsAuditLog]:
        """List audit logs with filters."""
        from sqlalchemy import select

        query = select(CmsAuditLog)
        if org_id:
            query = query.where(CmsAuditLog.org_id == org_id)
        if user_id:
            query = query.where(CmsAuditLog.user_id == user_id)
        if resource_type:
            query = query.where(CmsAuditLog.resource_type == resource_type)
        query = query.order_by(CmsAuditLog.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())


# Singleton
audit_svc = AuditService()
