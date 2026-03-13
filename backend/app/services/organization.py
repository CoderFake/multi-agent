"""
Organization service — CRUD + membership management with Redis caching.
Uses CacheService.get_or_set() for read-through + CacheInvalidation on mutation.
"""
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from app.core.exceptions import CmsException
from app.common.constants import ErrorCode
from app.config.settings import settings
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.cache.invalidation import CacheInvalidation
from app.models.organization import CmsOrganization, CmsOrgMembership
from app.models.user import CmsUser
from app.utils.logging import get_logger
from app.utils.storage import upload_file, delete_file, get_public_url, generate_path

logger = get_logger(__name__)


class OrganizationService:
    """Organization CRUD service with Redis cache."""

    async def create(
        self, db: AsyncSession, cache: CacheService,
        name: str, subdomain: str, timezone: str = "UTC",
    ) -> CmsOrganization:
        """Create a new organization. Invalidates system org cache."""
        slug = subdomain  # slug = subdomain

        existing = await db.execute(
            select(CmsOrganization).where(
                (CmsOrganization.slug == slug) | (CmsOrganization.subdomain == subdomain)
            )
        )
        if existing.scalar_one_or_none():
            raise CmsException(
                error_code=ErrorCode.ORG_SLUG_EXISTS,
                detail=f"Organization subdomain '{subdomain}' already exists",
                status_code=409,
            )

        org = CmsOrganization(
            name=name, slug=slug, subdomain=subdomain,
            timezone=timezone, is_active=True,
        )
        db.add(org)
        await db.commit()
        await db.refresh(org)
        logger.info(f"Organization created: {org.name} ({org.subdomain})")
        return org

    async def get(self, db: AsyncSession, cache: CacheService, org_id: str) -> dict:
        """Get organization by ID — cached."""

        async def _fetch():
            org = await db.get(CmsOrganization, org_id)
            if not org:
                return None
            return {
                "id": str(org.id),
                "name": org.name,
                "slug": org.slug,
                "subdomain": org.subdomain,
                "logo_url": get_public_url(org.logo_url, bucket=org.subdomain or org.slug),
                "timezone": org.timezone,
                "is_active": org.is_active,
                "created_at": org.created_at,
            }

        result = await cache.get_or_set(
            CacheKeys.org_info(org_id), _fetch, ttl=settings.CACHE_ORG_TTL
        )
        if not result:
            raise CmsException(
                error_code=ErrorCode.ORG_NOT_FOUND,
                detail="Organization not found",
                status_code=404,
            )
        return result

    async def get_model(self, db: AsyncSession, org_id: str) -> CmsOrganization:
        """Get org ORM model directly (no cache, for mutations)."""
        org = await db.get(CmsOrganization, org_id)
        if not org:
            raise CmsException(
                error_code=ErrorCode.ORG_NOT_FOUND,
                detail="Organization not found",
                status_code=404,
            )
        return org

    async def list_all(
        self, db: AsyncSession, page: int = 1, page_size: int = 20, search: Optional[str] = None
    ) -> tuple[list[dict], int]:
        """List organizations with member count. Not cached (paginated + search)."""
        query = (
            select(
                CmsOrganization,
                func.count(CmsOrgMembership.id).label("member_count"),
            )
            .outerjoin(CmsOrgMembership, CmsOrgMembership.org_id == CmsOrganization.id)
            .group_by(CmsOrganization.id)
        )
        if search:
            query = query.where(
                CmsOrganization.name.ilike(f"%{search}%")
                | CmsOrganization.slug.ilike(f"%{search}%")
            )

        count_query = select(func.count()).select_from(CmsOrganization)
        if search:
            count_query = count_query.where(
                CmsOrganization.name.ilike(f"%{search}%")
                | CmsOrganization.slug.ilike(f"%{search}%")
            )
        total = (await db.execute(count_query)).scalar() or 0

        query = query.order_by(CmsOrganization.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)

        items = []
        for org, member_count in result.all():
            items.append({
                "id": str(org.id),
                "name": org.name,
                "slug": org.slug,
                "timezone": org.timezone,
                "is_active": org.is_active,
                "created_at": org.created_at,
                "member_count": member_count,
            })

        return items, total

    async def update(
        self, db: AsyncSession, cache: CacheService, org_id: str, **kwargs
    ) -> CmsOrganization:
        """Update organization. Invalidates org cache."""
        org = await self.get_model(db, org_id)

        # If subdomain is being updated, validate uniqueness and sync slug
        new_subdomain = kwargs.get("subdomain")
        if new_subdomain and new_subdomain != org.subdomain:
            existing = await db.execute(
                select(CmsOrganization).where(
                    (CmsOrganization.subdomain == new_subdomain) | (CmsOrganization.slug == new_subdomain),
                    CmsOrganization.id != org_id,
                )
            )
            if existing.scalar_one_or_none():
                raise CmsException(
                    error_code=ErrorCode.ORG_SLUG_EXISTS,
                    detail=f"Subdomain '{new_subdomain}' already used",
                    status_code=409,
                )
            # Keep slug in sync with subdomain
            kwargs["slug"] = new_subdomain

        # Legacy slug-only check (if slug is sent without subdomain)
        if "slug" in kwargs and kwargs["slug"] and "subdomain" not in kwargs:
            existing = await db.execute(
                select(CmsOrganization).where(
                    CmsOrganization.slug == kwargs["slug"],
                    CmsOrganization.id != org_id,
                )
            )
            if existing.scalar_one_or_none():
                raise CmsException(
                    error_code=ErrorCode.ORG_SLUG_EXISTS,
                    detail=f"Slug '{kwargs['slug']}' already used",
                    status_code=409,
                )

        for key, value in kwargs.items():
            if value is not None and hasattr(org, key):
                setattr(org, key, value)

        await db.commit()
        await db.refresh(org)

        # Invalidate cache
        invalidation = CacheInvalidation(cache)
        await invalidation.clear_org_info(org_id)
        await invalidation.clear_org_config(org_id)

        return org

    async def delete(self, db: AsyncSession, cache: CacheService, org_id: str) -> None:
        """Delete organization. Invalidates all org caches."""
        org = await self.get_model(db, org_id)
        await db.delete(org)
        await db.commit()

        invalidation = CacheInvalidation(cache)
        await invalidation.clear_org_info(org_id)
        await invalidation.clear_org_config(org_id)
        await invalidation.clear_org_agents(org_id)
        await invalidation.clear_all_org_permissions(org_id)

        logger.info(f"Organization deleted: {org.slug}")

    async def add_member(
        self, db: AsyncSession, cache: CacheService, org_id: str, user_id: str, org_role: str = "member"
    ) -> CmsOrgMembership:
        """Add a member to organization. Invalidates user cache."""
        await self.get_model(db, org_id)
        user = await db.get(CmsUser, user_id)
        if not user:
            raise CmsException(
                error_code=ErrorCode.USER_NOT_FOUND, detail="User not found", status_code=404
            )

        existing = await db.execute(
            select(CmsOrgMembership).where(
                CmsOrgMembership.user_id == user_id,
                CmsOrgMembership.org_id == org_id,
            )
        )
        if existing.scalar_one_or_none():
            raise CmsException(
                error_code=ErrorCode.ORG_MEMBERSHIP_EXISTS,
                detail="User is already a member",
                status_code=409,
            )

        membership = CmsOrgMembership(
            user_id=user_id, org_id=org_id, org_role=org_role, is_active=True,
        )
        db.add(membership)
        await db.commit()
        await db.refresh(membership)

        # Invalidate user info cache (memberships changed)
        invalidation = CacheInvalidation(cache)
        await invalidation.clear_user_info(user_id)

        return membership

    async def list_members(self, db: AsyncSession, org_id: str) -> list[dict]:
        """List members of an organization."""
        result = await db.execute(
            select(CmsOrgMembership, CmsUser)
            .join(CmsUser, CmsOrgMembership.user_id == CmsUser.id)
            .where(CmsOrgMembership.org_id == org_id)
            .order_by(CmsOrgMembership.joined_at.desc())
        )
        members = []
        for membership, user in result.all():
            members.append({
                "user_id": str(user.id),
                "user_email": user.email,
                "user_full_name": user.full_name,
                "org_role": membership.org_role,
                "is_active": membership.is_active,
                "joined_at": membership.joined_at,
            })
        return members

    async def upload_logo(
        self, db: AsyncSession, cache: CacheService, org_id: str, file: UploadFile,
    ) -> str:
        """Upload org logo to S3 using org's subdomain as bucket."""
        allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        if file.content_type not in allowed_types:
            raise CmsException(
                error_code="INVALID_FILE_TYPE",
                detail=f"Allowed types: {', '.join(allowed_types)}",
                status_code=400,
            )

        result = await db.execute(
            select(CmsOrganization).where(CmsOrganization.id == org_id)
        )
        org = result.scalar_one_or_none()
        if not org:
            raise CmsException(
                error_code=ErrorCode.ORG_NOT_FOUND,
                detail="Organization not found",
                status_code=404,
            )

        bucket = org.subdomain or org.slug

        # Delete old logo if exists
        if org.logo_url:
            await delete_file(org.logo_url, bucket=bucket)

        # Upload new
        path = generate_path("logo", file.filename or "logo.jpg")
        storage_path = await upload_file(file, path, bucket=bucket)

        # Save to DB
        org.logo_url = storage_path
        await db.commit()

        # Invalidate org cache so next GET returns updated logo_url
        invalidation = CacheInvalidation(cache)
        await invalidation.clear_org_info(org_id)

        return get_public_url(storage_path, bucket=bucket)


# Singleton
org_svc = OrganizationService()
