"""
Tenant permission service — list available permissions for admin assignment.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import CmsPermission, CmsContentType
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TenantPermissionService:
    """Permission listing within an org context."""

    async def list_all_permissions(self, db: AsyncSession) -> list[dict]:
        """List all available permissions (for admin to assign to groups)."""
        result = await db.execute(
            select(CmsPermission, CmsContentType)
            .join(CmsContentType, CmsPermission.content_type_id == CmsContentType.id)
            .order_by(CmsContentType.app_label, CmsPermission.codename)
        )
        return [
            {
                "id": str(perm.id),
                "codename": perm.codename,
                "name": perm.name,
                "app_label": ct.app_label,
                "model": ct.model,
            }
            for perm, ct in result.all()
        ]


# Singleton
tenant_perm_svc = TenantPermissionService()
