"""
Tenant user service — manage users within an organization.
Uses CacheService.get_or_set() for reads + CacheInvalidation on mutation.
"""
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CmsException
from app.common.constants import ErrorCode, NotificationType, NotificationCode
from app.config.settings import settings
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation
from app.models.user import CmsUser
from app.models.organization import CmsOrgMembership
from app.utils.logging import get_logger
from app.services.notification import notification_svc
from app.common.constants import ROLE_HIERARCHY

logger = get_logger(__name__)


class TenantUserService:
    """User management within an org — list, get, update, remove."""

    async def list_users(
        self, db: AsyncSession, cache: CacheService, org_id: str,
        page: int = 1, page_size: int = 20, search: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        """
        List org members with user info.
        Cached when no search filter (full list). Paginated + search = no cache.
        """
        # If no search, cache the full list and paginate in-memory
        if not search:
            all_users = await cache.get_or_set(
                CacheKeys.org_users(org_id),
                lambda: self._fetch_all_users(db, org_id),
                ttl=settings.CACHE_USER_TTL,
            )
            if all_users is None:
                all_users = []

            total = len(all_users)
            start = (page - 1) * page_size
            items = all_users[start:start + page_size]
            return items, total

        # With search — always from DB (not cached)
        return await self._fetch_users_filtered(db, org_id, page, page_size, search)

    async def get_user(self, db: AsyncSession, org_id: str, user_id: str) -> dict:
        """Get a single user's info within an org."""
        result = await db.execute(
            select(CmsOrgMembership, CmsUser)
            .join(CmsUser, CmsOrgMembership.user_id == CmsUser.id)
            .where(
                CmsOrgMembership.org_id == org_id,
                CmsOrgMembership.user_id == user_id,
            )
        )
        row = result.first()
        if not row:
            raise CmsException(
                error_code=ErrorCode.USER_NOT_FOUND,
                detail="User not found in this organization",
                status_code=404,
            )
        membership, user = row
        return {
            "user_id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "org_role": membership.org_role,
            "is_active": membership.is_active,
            "joined_at": membership.joined_at,
        }

    async def update_user(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, user_id: str,
        acting_user_id: str | None = None,
        acting_user_role: str | None = None,
        **kwargs,
    ) -> dict:
        """Update user membership (role, active status). Enforces role hierarchy."""
        result = await db.execute(
            select(CmsOrgMembership).where(
                CmsOrgMembership.org_id == org_id,
                CmsOrgMembership.user_id == user_id,
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise CmsException(
                error_code=ErrorCode.USER_NOT_FOUND,
                detail="User not found in this organization",
                status_code=404,
            )

        # ── Role hierarchy enforcement ──────────────────────────────
        if acting_user_role and acting_user_role != "superuser":
            actor_level = ROLE_HIERARCHY.get(acting_user_role, 0)
            target_level = ROLE_HIERARCHY.get(membership.org_role, 0)

            # Cannot edit someone with equal or higher role
            if target_level >= actor_level:
                raise CmsException(
                    error_code=ErrorCode.AUTH_FORBIDDEN,
                    detail="Cannot modify a user with equal or higher role",
                    status_code=403,
                )

            # Cannot assign a role equal or higher than your own
            new_role = kwargs.get("org_role")
            if new_role:
                new_level = ROLE_HIERARCHY.get(new_role, 0)
                if new_level >= actor_level:
                    raise CmsException(
                        error_code=ErrorCode.AUTH_FORBIDDEN,
                        detail="Cannot assign a role equal to or higher than your own",
                        status_code=403,
                    )

        for key, value in kwargs.items():
            if value is not None and hasattr(membership, key):
                setattr(membership, key, value)

        await db.commit()
        await db.refresh(membership)

        # Invalidate: user list + user permissions (role change may affect perms) + membership
        inv = CacheInvalidation(cache)
        await inv.clear_org_users(org_id)
        await inv.clear_user_permissions(user_id, org_id)
        await inv.clear_user_info(user_id)
        await inv.clear_membership(user_id, org_id)

        # Notify user about role change
        if 'org_role' in kwargs and kwargs['org_role'] is not None:
            await notification_svc.create(
                db, user_id, org_id,
                NotificationType.ROLE_CHANGED,
                NotificationCode.ROLE_CHANGED,
                NotificationCode.ROLE_CHANGED_DESC,
                {"new_role": kwargs['org_role']},
            )

        return await self.get_user(db, org_id, user_id)

    async def remove_member(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, user_id: str,
        acting_user_id: str | None = None,
        acting_user_role: str | None = None,
    ) -> None:
        """Remove a user from the organization. Enforces role hierarchy."""
        result = await db.execute(
            select(CmsOrgMembership).where(
                CmsOrgMembership.org_id == org_id,
                CmsOrgMembership.user_id == user_id,
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise CmsException(
                error_code=ErrorCode.USER_NOT_FOUND,
                detail="User not found in this organization",
                status_code=404,
            )

        # ── Role hierarchy enforcement ──────────────────────────────
        if acting_user_role and acting_user_role != "superuser":
            actor_level = ROLE_HIERARCHY.get(acting_user_role, 0)
            target_level = ROLE_HIERARCHY.get(membership.org_role, 0)

            if target_level >= actor_level:
                raise CmsException(
                    error_code=ErrorCode.AUTH_FORBIDDEN,
                    detail="Cannot remove a user with equal or higher role",
                    status_code=403,
                )

        await db.delete(membership)
        await db.commit()

        # Cascading invalidation: user list + user info + user perms + membership + org groups
        inv = CacheInvalidation(cache)
        await inv.clear_org_users(org_id)
        await inv.clear_user_info(user_id)
        await inv.clear_user_permissions(user_id, org_id)
        await inv.clear_membership(user_id, org_id)
        await inv.clear_org_groups(org_id)  # member counts change

        logger.info(f"Removed user {user_id} from org {org_id}")

        # Notify removed user
        await notification_svc.create(
            db, user_id, org_id,
            NotificationType.MEMBER_REMOVED,
            NotificationCode.MEMBER_REMOVED,
            NotificationCode.MEMBER_REMOVED_DESC,
        )

    # ── Internal fetchers ────────────────────────────────────────────────

    async def _fetch_all_users(self, db: AsyncSession, org_id: str) -> list[dict]:
        """Fetch all users in org from DB (for caching)."""
        result = await db.execute(
            select(CmsOrgMembership, CmsUser)
            .join(CmsUser, CmsOrgMembership.user_id == CmsUser.id)
            .where(
                CmsOrgMembership.org_id == org_id,
                CmsUser.deleted_at.is_(None),
            )
            .order_by(CmsOrgMembership.joined_at.desc())
        )
        return [
            {
                "user_id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "org_role": membership.org_role,
                "is_active": membership.is_active,
                "joined_at": membership.joined_at,
            }
            for membership, user in result.all()
        ]

    async def _fetch_users_filtered(
        self, db: AsyncSession, org_id: str,
        page: int, page_size: int, search: str,
    ) -> tuple[list[dict], int]:
        """Fetch users with search — no cache."""
        query = (
            select(CmsOrgMembership, CmsUser)
            .join(CmsUser, CmsOrgMembership.user_id == CmsUser.id)
            .where(
                CmsOrgMembership.org_id == org_id,
                CmsUser.deleted_at.is_(None),
                CmsUser.full_name.ilike(f"%{search}%")
                | CmsUser.email.ilike(f"%{search}%"),
            )
        )

        count_q = (
            select(func.count(CmsOrgMembership.id))
            .join(CmsUser, CmsOrgMembership.user_id == CmsUser.id)
            .where(
                CmsOrgMembership.org_id == org_id,
                CmsUser.deleted_at.is_(None),
                CmsUser.full_name.ilike(f"%{search}%")
                | CmsUser.email.ilike(f"%{search}%"),
            )
        )
        total = (await db.execute(count_q)).scalar() or 0

        query = query.order_by(CmsOrgMembership.joined_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)

        items = [
            {
                "user_id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "org_role": membership.org_role,
                "is_active": membership.is_active,
                "joined_at": membership.joined_at,
            }
            for membership, user in result.all()
        ]
        return items, total


# Singleton
tenant_user_svc = TenantUserService()
