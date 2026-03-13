"""
Permission service — RBAC permission resolution with Redis caching.
Resolution: is_superuser(system only) → User override → Group → Denied.
"""
import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.cache.keys import CacheKeys
from app.models.user import CmsUser
from app.models.group import CmsGroup, cms_user_groups, cms_group_permissions, CmsUserPermission
from app.models.permission import CmsPermission, CmsContentType
from app.models.organization import CmsOrgMembership
from app.models.resource_permission import CmsResourcePermission
from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class PermissionService:
    """RBAC permission resolution service."""

    async def check_permission(
        self,
        db: AsyncSession,
        redis: Redis,
        user_id: str,
        org_id: str,
        codename: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Check if user has permission in org.
        Returns (granted, reason).
        Resolution order: superuser → resource override → user override → group → denied.
        """
        # 1) Superuser — full access to everything (system + tenant)
        user = await db.get(CmsUser, user_id)
        if not user:
            return False, "user_not_found"
        if user.is_superuser:
            return True, "superuser"

        # 2) Check membership + org_role
        membership_result = await db.execute(
            select(CmsOrgMembership).where(
                CmsOrgMembership.user_id == user_id,
                CmsOrgMembership.org_id == org_id,
                CmsOrgMembership.is_active.is_(True),
            )
        )
        membership = membership_result.scalar_one_or_none()
        if not membership:
            return False, "not_member"

        # 3) Owner — full access to everything in org
        if membership.org_role == "owner":
            return True, "owner"

        # 4) Admin — full access except destructive user ops
        if membership.org_role == "admin":
            return True, "admin"

        # 3) Resource-level override (if applicable)
        if resource_type and resource_id:
            perm_obj = await self._find_permission(db, codename)
            if perm_obj:
                res_perm = await db.execute(
                    select(CmsResourcePermission).where(
                        CmsResourcePermission.permission_id == perm_obj.id,
                        CmsResourcePermission.resource_type == resource_type,
                        CmsResourcePermission.resource_id == resource_id,
                        CmsResourcePermission.org_id == org_id,
                        (CmsResourcePermission.user_id == user_id) | (CmsResourcePermission.user_id.is_(None)),
                    )
                )
                for rp in res_perm.scalars().all():
                    if rp.user_id and str(rp.user_id) == user_id:
                        return rp.is_granted, "resource_user_override"
                    if rp.group_id:
                        # Check if user in this group
                        pass  # simplified — group resource override

        # 4) User-level override
        perm = await self._find_permission(db, codename)
        if perm:
            user_override = await db.execute(
                select(CmsUserPermission).where(
                    CmsUserPermission.user_id == user_id,
                    CmsUserPermission.permission_id == perm.id,
                    CmsUserPermission.org_id == org_id,
                )
            )
            uo = user_override.scalar_one_or_none()
            if uo is not None:
                return uo.is_granted, "user_override"

        # 5) Group-level
        if perm:
            # Get user's groups in this org
            user_group_ids = await self._get_user_group_ids(db, user_id, org_id)
            if user_group_ids:
                group_perm = await db.execute(
                    select(cms_group_permissions).where(
                        cms_group_permissions.c.group_id.in_(user_group_ids),
                        cms_group_permissions.c.permission_id == perm.id,
                    )
                )
                if group_perm.fetchone():
                    return True, "group"

        # 6) Denied
        return False, "denied"

    async def get_user_permissions(
        self, db: AsyncSession, redis: Redis, user_id: str, org_id: str
    ) -> set[str]:
        """Get all resolved permission codenames for user in org. Cached in Redis."""
        cache_key = CacheKeys.user_permissions(user_id, org_id)

        # Check cache
        cached = await redis.get(cache_key)
        if cached:
            return set(json.loads(cached))

        # Check org_role — owner/admin get all permissions automatically
        membership_result = await db.execute(
            select(CmsOrgMembership).where(
                CmsOrgMembership.user_id == user_id,
                CmsOrgMembership.org_id == org_id,
                CmsOrgMembership.is_active.is_(True),
            )
        )
        membership = membership_result.scalar_one_or_none()

        if membership and membership.org_role in ("owner", "admin"):
            # Owner/admin: get ALL permission codenames from DB
            all_perms_result = await db.execute(select(CmsPermission.codename))
            permissions = set(row[0] for row in all_perms_result.all())
            await redis.setex(cache_key, settings.CACHE_PERMISSION_TTL, json.dumps(list(permissions)))
            return permissions

        # Resolve from DB for regular members
        permissions: set[str] = set()

        # User overrides (granted)
        result = await db.execute(
            select(CmsPermission.codename)
            .join(CmsUserPermission, CmsUserPermission.permission_id == CmsPermission.id)
            .where(
                CmsUserPermission.user_id == user_id,
                CmsUserPermission.org_id == org_id,
                CmsUserPermission.is_granted.is_(True),
            )
        )
        permissions.update(row[0] for row in result.all())

        # Denied overrides
        denied_result = await db.execute(
            select(CmsPermission.codename)
            .join(CmsUserPermission, CmsUserPermission.permission_id == CmsPermission.id)
            .where(
                CmsUserPermission.user_id == user_id,
                CmsUserPermission.org_id == org_id,
                CmsUserPermission.is_granted.is_(False),
            )
        )
        denied = set(row[0] for row in denied_result.all())

        # Group permissions
        user_group_ids = await self._get_user_group_ids(db, user_id, org_id)
        if user_group_ids:
            group_result = await db.execute(
                select(CmsPermission.codename)
                .join(cms_group_permissions, cms_group_permissions.c.permission_id == CmsPermission.id)
                .where(cms_group_permissions.c.group_id.in_(user_group_ids))
            )
            group_perms = set(row[0] for row in group_result.all())
            # Add group perms that aren't explicitly denied
            permissions.update(group_perms - denied)

        # Cache
        await redis.setex(cache_key, settings.CACHE_PERMISSION_TTL, json.dumps(list(permissions)))

        return permissions

    async def get_ui_permissions(
        self, db: AsyncSession, redis: Redis, user_id: str, org_id: str
    ) -> dict:
        """
        Get UI-specific permissions for frontend rendering.
        Returns nav_items (visible pages) and actions (per resource_type).
        """
        permissions = await self.get_user_permissions(db, redis, user_id, org_id)

        # Map permission codenames to nav items
        nav_items = []
        action_map: dict[str, list[str]] = {}

        for perm in permissions:
            parts = perm.split(".")
            if len(parts) == 2:
                resource, action = parts
                # Nav: if user can view, add nav item
                if action == "view":
                    nav_items.append(resource)
                # Actions
                if resource not in action_map:
                    action_map[resource] = []
                action_map[resource].append(action)

        return {
            "user_id": user_id,
            "org_id": org_id,
            "nav_items": sorted(set(nav_items)),
            "actions": action_map,
        }

    async def _find_permission(self, db: AsyncSession, codename: str) -> Optional[CmsPermission]:
        """Find a permission by codename."""
        result = await db.execute(
            select(CmsPermission).where(CmsPermission.codename == codename)
        )
        return result.scalar_one_or_none()

    async def _get_user_group_ids(self, db: AsyncSession, user_id: str, org_id: str) -> list:
        """Get group IDs the user belongs to in this org."""
        result = await db.execute(
            select(cms_user_groups.c.group_id)
            .join(CmsGroup, CmsGroup.id == cms_user_groups.c.group_id)
            .where(
                cms_user_groups.c.user_id == user_id,
                CmsGroup.org_id == org_id,
            )
        )
        return [row[0] for row in result.all()]


# Singleton
permission_svc = PermissionService()
