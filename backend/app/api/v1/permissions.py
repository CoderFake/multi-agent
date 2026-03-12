"""
Permission API — check permission, get user/UI permissions.
Used by frontend for permission-based rendering.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.dependencies import get_db_session, get_redis, require_org_membership
from app.common.types import CurrentUser
from app.schemas.permission import PermCheckRequest, PermCheckResponse, UserPermissionsResponse, UIPermissionsResponse
from app.services.permission import permission_svc

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("/me", response_model=UIPermissionsResponse)
async def get_my_ui_permissions(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    user: CurrentUser = Depends(require_org_membership),
):
    """Get UI permissions for current user in current org. Used by frontend."""
    result = await permission_svc.get_ui_permissions(db, redis, user.user_id, user.org_id)
    return result


@router.post("/check", response_model=PermCheckResponse)
async def check_permission(
    data: PermCheckRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    user: CurrentUser = Depends(require_org_membership),
):
    """Check if a user has a specific permission."""
    granted, reason = await permission_svc.check_permission(
        db, redis, data.user_id, user.org_id,
        data.codename, data.resource_type, data.resource_id,
    )
    return {"granted": granted, "reason": reason}
