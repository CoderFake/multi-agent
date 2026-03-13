"""
Tenant group service — CRUD + permission assignment + member management.
Uses CacheService.get_or_set() for reads + CacheInvalidation on mutation.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CmsException
from app.common.constants import ErrorCode, NotificationType, NotificationCode
from app.config.settings import settings
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation
from app.models.group import CmsGroup, cms_user_groups, cms_group_permissions
from app.models.permission import CmsPermission
from app.utils.logging import get_logger
from app.services.notification import notification_svc

logger = get_logger(__name__)


class TenantGroupService:
    """Group CRUD + permission/member management within an org."""

    async def list_groups(self, db: AsyncSession, cache: CacheService, org_id: str) -> list[dict]:
        """List all groups in an org with member + permission counts. Cached."""

        async def _fetch():
            member_count_sq = (
                select(func.count(cms_user_groups.c.user_id))
                .where(cms_user_groups.c.group_id == CmsGroup.id)
                .correlate(CmsGroup)
                .scalar_subquery()
            )
            perm_count_sq = (
                select(func.count(cms_group_permissions.c.permission_id))
                .where(cms_group_permissions.c.group_id == CmsGroup.id)
                .correlate(CmsGroup)
                .scalar_subquery()
            )
            result = await db.execute(
                select(CmsGroup, member_count_sq.label("mc"), perm_count_sq.label("pc"))
                .where(CmsGroup.org_id == org_id)
                .order_by(CmsGroup.created_at.desc())
            )
            return [
                {
                    "id": str(g.id),
                    "org_id": str(g.org_id) if g.org_id else None,
                    "name": g.name,
                    "description": g.description,
                    "is_system_default": g.is_system_default,
                    "member_count": mc or 0,
                    "permission_count": pc or 0,
                }
                for g, mc, pc in result.all()
            ]

        return await cache.get_or_set(
            CacheKeys.org_groups(org_id), _fetch, ttl=settings.CACHE_DEFAULT_TTL,
        ) or []

    async def create_group(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, name: str, description: Optional[str] = None,
    ) -> CmsGroup:
        """Create a new group in the org. Invalidates group cache."""
        group = CmsGroup(
            org_id=org_id,
            name=name,
            description=description,
            is_system_default=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(group)
        await db.commit()
        await db.refresh(group)

        inv = CacheInvalidation(cache)
        await inv.clear_org_groups(org_id)

        logger.info(f"Group created: {group.name} in org {org_id}")
        return group

    async def update_group(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, group_id: str, **kwargs,
    ) -> CmsGroup:
        """Update a group. Invalidates group cache."""
        group = await self._get_group(db, org_id, group_id)
        if group.is_system_default:
            raise CmsException(
                error_code=ErrorCode.AUTH_FORBIDDEN,
                detail="Cannot modify system default group",
                status_code=403,
            )

        for key, value in kwargs.items():
            if value is not None and hasattr(group, key):
                setattr(group, key, value)

        await db.commit()
        await db.refresh(group)

        inv = CacheInvalidation(cache)
        await inv.clear_org_groups(org_id)

        return group

    async def delete_group(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, group_id: str,
    ) -> None:
        """Delete a group. Cascading: clears groups + all org permissions."""
        group = await self._get_group(db, org_id, group_id)
        if group.is_system_default:
            raise CmsException(
                error_code=ErrorCode.AUTH_FORBIDDEN,
                detail="Cannot delete system default group",
                status_code=403,
            )

        await db.delete(group)
        await db.commit()

        # Cascading invalidation: groups + all user permissions (group deleted)
        inv = CacheInvalidation(cache)
        await inv.clear_org_groups(org_id)
        await inv.clear_all_org_permissions(org_id)
        await inv.clear_org_users(org_id)  # member counts may change

        logger.info(f"Group deleted: {group.name} in org {org_id}")

        # Notify all former group members
        members = await self.get_group_members(db, group_id)
        if members:
            member_ids = [m["user_id"] for m in members]
            await notification_svc.create_bulk(
                db, member_ids, org_id,
                NotificationType.GROUP_DELETED,
                NotificationCode.GROUP_DELETED,
                NotificationCode.GROUP_DELETED_DESC,
                {"group_name": group.name},
            )

    # ── Permission Management ────────────────────────────────────────────

    async def assign_permissions(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, group_id: str, permission_ids: list[str],
    ) -> None:
        """Assign permissions to a group. Cascading: clears groups + ALL org perms."""
        await self._get_group(db, org_id, group_id)

        for pid in permission_ids:
            existing = await db.execute(
                select(cms_group_permissions).where(
                    cms_group_permissions.c.group_id == group_id,
                    cms_group_permissions.c.permission_id == pid,
                )
            )
            if not existing.fetchone():
                await db.execute(
                    cms_group_permissions.insert().values(group_id=group_id, permission_id=pid)
                )

        await db.commit()

        # Cascading: groups cache + ALL user permissions in org
        inv = CacheInvalidation(cache)
        await inv.clear_org_groups(org_id)
        await inv.clear_all_org_permissions(org_id)

        # Notify all group members about permission change
        members = await self.get_group_members(db, group_id)
        if members:
            member_ids = [m["user_id"] for m in members]
            await notification_svc.create_bulk(
                db, member_ids, org_id,
                NotificationType.PERMISSION_UPDATED,
                NotificationCode.PERMISSION_UPDATED,
                NotificationCode.PERMISSION_ASSIGNED_DESC,
            )

    async def revoke_permissions(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, group_id: str, permission_ids: list[str],
    ) -> None:
        """Revoke permissions from a group. Cascading: clears groups + ALL org perms."""
        await self._get_group(db, org_id, group_id)

        await db.execute(
            delete(cms_group_permissions).where(
                cms_group_permissions.c.group_id == group_id,
                cms_group_permissions.c.permission_id.in_(permission_ids),
            )
        )
        await db.commit()

        # Cascading: groups cache + ALL user permissions in org
        inv = CacheInvalidation(cache)
        await inv.clear_org_groups(org_id)
        await inv.clear_all_org_permissions(org_id)

        # Notify all group members about permission revoke
        members = await self.get_group_members(db, group_id)
        if members:
            member_ids = [m["user_id"] for m in members]
            await notification_svc.create_bulk(
                db, member_ids, org_id,
                NotificationType.PERMISSION_UPDATED,
                NotificationCode.PERMISSION_UPDATED,
                NotificationCode.PERMISSION_REVOKED_DESC,
            )

    # ── Member Management ────────────────────────────────────────────────

    async def add_member(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, group_id: str, user_id: str,
    ) -> None:
        """Add user to group. Cascading: groups + user permissions."""
        await self._get_group(db, org_id, group_id)

        existing = await db.execute(
            select(cms_user_groups).where(
                cms_user_groups.c.group_id == group_id,
                cms_user_groups.c.user_id == user_id,
            )
        )
        if existing.fetchone():
            raise CmsException(
                error_code=ErrorCode.ORG_MEMBERSHIP_EXISTS,
                detail="User is already in this group",
                status_code=409,
            )

        await db.execute(
            cms_user_groups.insert().values(group_id=group_id, user_id=user_id)
        )
        await db.commit()

        # Cascading: groups (member count) + this user's permissions
        inv = CacheInvalidation(cache)
        await inv.clear_org_groups(org_id)
        await inv.clear_user_permissions(user_id, org_id)

        # Notify user
        group = await self._get_group(db, org_id, group_id)
        await notification_svc.create(
            db, user_id, org_id,
            NotificationType.GROUP_ADDED,
            NotificationCode.GROUP_ADDED,
            NotificationCode.GROUP_ADDED_DESC,
            {"group_id": group_id, "group_name": group.name},
        )

    async def remove_member(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, group_id: str, user_id: str,
    ) -> None:
        """Remove user from group. Cascading: groups + user permissions."""
        await self._get_group(db, org_id, group_id)

        result = await db.execute(
            delete(cms_user_groups).where(
                cms_user_groups.c.group_id == group_id,
                cms_user_groups.c.user_id == user_id,
            )
        )
        if result.rowcount == 0:
            raise CmsException(
                error_code=ErrorCode.GROUP_NOT_FOUND,
                detail="User is not in this group",
                status_code=404,
            )
        await db.commit()

        # Cascading: groups (member count) + this user's permissions
        inv = CacheInvalidation(cache)
        await inv.clear_org_groups(org_id)
        await inv.clear_user_permissions(user_id, org_id)

        # Notify user
        group = await self._get_group(db, org_id, group_id)
        await notification_svc.create(
            db, user_id, org_id,
            NotificationType.GROUP_REMOVED,
            NotificationCode.GROUP_REMOVED,
            NotificationCode.GROUP_REMOVED_DESC,
            {"group_id": group_id, "group_name": group.name},
        )

    async def get_group_permissions(self, db: AsyncSession, group_id: str) -> list[dict]:
        """Get permissions assigned to a group."""
        result = await db.execute(
            select(CmsPermission)
            .join(cms_group_permissions, cms_group_permissions.c.permission_id == CmsPermission.id)
            .where(cms_group_permissions.c.group_id == group_id)
        )
        return [
            {"id": str(p.id), "codename": p.codename, "name": p.name}
            for p in result.scalars().all()
        ]

    async def get_group_members(self, db: AsyncSession, group_id: str) -> list[dict]:
        """Get users in a group."""
        from app.models.user import CmsUser
        result = await db.execute(
            select(CmsUser)
            .join(cms_user_groups, cms_user_groups.c.user_id == CmsUser.id)
            .where(cms_user_groups.c.group_id == group_id)
        )
        return [
            {"user_id": str(u.id), "email": u.email, "full_name": u.full_name}
            for u in result.scalars().all()
        ]

    # ── Internal ─────────────────────────────────────────────────────────

    async def _get_group(self, db: AsyncSession, org_id: str, group_id: str) -> CmsGroup:
        """Get group by ID within org. Raises 404 if not found."""
        result = await db.execute(
            select(CmsGroup).where(
                CmsGroup.id == group_id,
                CmsGroup.org_id == org_id,
            )
        )
        group = result.scalar_one_or_none()
        if not group:
            raise CmsException(
                error_code=ErrorCode.GROUP_NOT_FOUND,
                detail="Group not found",
                status_code=404,
            )
        return group


# Singleton
tenant_group_svc = TenantGroupService()
