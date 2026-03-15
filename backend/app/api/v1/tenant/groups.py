"""
Tenant Group API — CRUD + permission assignment + member management.
Permission-protected via require_permission().
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_permission
from app.common.types import CurrentUser
from app.cache.service import CacheService
from app.schemas.group import GroupCreate, GroupUpdate, GroupResponse, GroupListResponse, PermissionAssign, GroupMemberAction
from app.services.tenant_group import tenant_group_svc
from app.services.audit import audit_svc

router = APIRouter(prefix="/groups", tags=["tenant-groups"])


@router.get("", response_model=GroupListResponse)
async def list_groups(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("group.view")),
):
    """List all groups in the current org."""
    items = await tenant_group_svc.list_groups(db, cache, user.org_id)
    return {"items": items, "total": len(items)}


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    data: GroupCreate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("group.create")),
):
    """Create a new group in the org."""
    group = await tenant_group_svc.create_group(
        db, cache, user.org_id, data.name, data.description,
    )
    await audit_svc.log_action(
        db, user.user_id, "create", "group", str(group.id),
        org_id=user.org_id, new_values=data.model_dump(),
    )
    return {
        "id": str(group.id), "org_id": str(group.org_id),
        "name": group.name, "description": group.description,
        "is_system_default": group.is_system_default,
        "member_count": 0, "permission_count": 0,
    }


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    data: GroupUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("group.update")),
):
    """Update a group."""
    group = await tenant_group_svc.update_group(
        db, cache, user.org_id, group_id,
        **data.model_dump(exclude_unset=True),
    )
    await audit_svc.log_action(
        db, user.user_id, "update", "group", group_id,
        org_id=user.org_id, new_values=data.model_dump(exclude_unset=True),
    )
    return {
        "id": str(group.id), "org_id": str(group.org_id),
        "name": group.name, "description": group.description,
        "is_system_default": group.is_system_default,
        "member_count": 0, "permission_count": 0,
    }


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("group.delete")),
):
    """Delete a group."""
    await tenant_group_svc.delete_group(db, cache, user.org_id, group_id)
    await audit_svc.log_action(
        db, user.user_id, "delete", "group", group_id, org_id=user.org_id,
    )


# ── Permission Assignment ────────────────────────────────────────────────

@router.post("/{group_id}/permissions", status_code=204)
async def assign_permissions(
    group_id: str,
    data: PermissionAssign,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("permission.assign")),
):
    """Assign permissions to a group."""
    await tenant_group_svc.assign_permissions(
        db, cache, user.org_id, group_id, data.permission_ids,
    )
    await audit_svc.log_action(
        db, user.user_id, "assign_permissions", "group", group_id,
        org_id=user.org_id, new_values={"permission_ids": data.permission_ids},
    )


@router.delete("/{group_id}/permissions", status_code=204)
async def revoke_permissions(
    group_id: str,
    data: PermissionAssign,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("permission.revoke")),
):
    """Revoke permissions from a group."""
    await tenant_group_svc.revoke_permissions(
        db, cache, user.org_id, group_id, data.permission_ids,
    )
    await audit_svc.log_action(
        db, user.user_id, "revoke_permissions", "group", group_id,
        org_id=user.org_id, new_values={"permission_ids": data.permission_ids},
    )


@router.get("/{group_id}/permissions")
async def get_group_permissions(
    group_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("permission.view")),
):
    """Get permissions assigned to a group."""
    return await tenant_group_svc.get_group_permissions(db, group_id)


# ── Member Management ────────────────────────────────────────────────────

@router.post("/{group_id}/members", status_code=204)
async def add_members(
    group_id: str,
    data: GroupMemberAction,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("group.update")),
):
    """Add one or more users to a group."""
    for uid in data.user_ids:
        await tenant_group_svc.add_member(
            db, cache, user.org_id, group_id, uid,
        )
        await audit_svc.log_action(
            db, user.user_id, "add_member", "group", group_id,
            org_id=user.org_id, new_values={"member_user_id": uid},
        )


@router.delete("/{group_id}/members/{member_user_id}", status_code=204)
async def remove_member(
    group_id: str,
    member_user_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("group.update")),
):
    """Remove a user from a group."""
    await tenant_group_svc.remove_member(
        db, cache, user.org_id, group_id, member_user_id,
    )
    await audit_svc.log_action(
        db, user.user_id, "remove_member", "group", group_id,
        org_id=user.org_id, new_values={"member_user_id": member_user_id},
    )


@router.get("/{group_id}/members")
async def get_group_members(
    group_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("group.view")),
):
    """Get users in a group."""
    return await tenant_group_svc.get_group_members(db, group_id)
