"""
Tenant User API — CRUD user membership within an org.
Permission-protected via require_permission().
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_permission
from app.common.types import CurrentUser
from app.cache.service import CacheService
from app.schemas.user import UserResponse, UserListResponse, UserUpdate
from app.services.tenant_user import tenant_user_svc
from app.services.audit import audit_svc

router = APIRouter(prefix="/users", tags=["tenant-users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("user.view")),
):
    """List users/members in the current org."""
    items, total = await tenant_user_svc.list_users(db, cache, user.org_id, page, page_size, search)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("user.view")),
):
    """Get a user's info within the org."""
    return await tenant_user_svc.get_user(db, user.org_id, user_id)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("user.update")),
):
    """Update user role or active status within the org."""
    result = await tenant_user_svc.update_user(
        db, cache, user.org_id, user_id,
        acting_user_id=user.user_id,
        acting_user_role=user.org_role,
        **data.model_dump(exclude_unset=True),
    )
    await audit_svc.log_action(
        db, user.user_id, "update", "user", user_id,
        org_id=user.org_id, new_values=data.model_dump(exclude_unset=True),
    )
    return result


@router.delete("/{user_id}", status_code=204)
async def remove_user(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("user.delete")),
):
    """Remove a user from the org."""
    await tenant_user_svc.remove_member(
        db, cache, user.org_id, user_id,
        acting_user_id=user.user_id,
        acting_user_role=user.org_role,
    )
    await audit_svc.log_action(
        db, user.user_id, "remove", "user", user_id, org_id=user.org_id,
    )
