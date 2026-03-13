"""
Tenant Permissions API — list all available permissions.
Router = thin delegation only. All logic in tenant_perm_svc.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_org_membership
from app.common.types import CurrentUser
from app.services.tenant_permission import tenant_perm_svc

router = APIRouter(prefix="/permissions", tags=["tenant-permissions"])


@router.get("")
async def list_permissions(
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_org_membership),
):
    """List all available permissions (for admin to assign to groups)."""
    return await tenant_perm_svc.list_all_permissions(db)
