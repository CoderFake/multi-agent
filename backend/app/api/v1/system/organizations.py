"""
System API — Organization CRUD (superuser only).
Router is thin — delegates all logic to org_svc.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_superuser
from app.common.types import CurrentUser
from app.common.constants import Pagination
from app.schemas.organization import OrgCreate, OrgUpdate, OrgResponse, OrgListResponse, MembershipResponse, AddMemberRequest
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.cache.service import CacheService
from app.services.organization import org_svc
from app.services.audit import audit_svc

router = APIRouter(prefix="/organizations", tags=["system-organizations"])


@router.get("", response_model=PaginatedResponse[OrgListResponse])
async def list_organizations(
    page: int = Pagination.DEFAULT_PAGE,
    page_size: int = Pagination.DEFAULT_SIZE,
    search: str | None = None,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_superuser),
):
    """List all organizations with member counts."""
    items, total = await org_svc.list_all(db, page=page, page_size=page_size, search=search)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.post("", response_model=OrgResponse, status_code=201)
async def create_organization(
    data: OrgCreate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Create a new organization."""
    org = await org_svc.create(db, cache, name=data.name, slug=data.slug, timezone=data.timezone)
    await audit_svc.log_action(
        db, user_id=user.user_id, action="create",
        resource_type="organization", resource_id=str(org.id),
        new_values={"name": org.name, "slug": org.slug},
    )
    return org


@router.get("/{org_id}", response_model=OrgResponse)
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Get organization by ID."""
    return await org_svc.get(db, cache, org_id)


@router.put("/{org_id}", response_model=OrgResponse)
async def update_organization(
    org_id: str,
    data: OrgUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Update organization."""
    org = await org_svc.update(db, cache, org_id, **data.model_dump(exclude_unset=True))
    await audit_svc.log_action(
        db, user_id=user.user_id, action="update",
        resource_type="organization", resource_id=str(org.id),
        new_values=data.model_dump(exclude_unset=True),
    )
    return org


@router.delete("/{org_id}", response_model=SuccessResponse)
async def delete_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Delete organization."""
    await org_svc.delete(db, cache, org_id)
    await audit_svc.log_action(
        db, user_id=user.user_id, action="delete",
        resource_type="organization", resource_id=org_id,
    )
    return {"message": "Organization deleted successfully"}


@router.get("/{org_id}/members", response_model=list[MembershipResponse])
async def list_members(
    org_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_superuser),
):
    """List organization members."""
    return await org_svc.list_members(db, org_id)


@router.post("/{org_id}/members", response_model=SuccessResponse, status_code=201)
async def add_member(
    org_id: str,
    data: AddMemberRequest,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Add a member to organization."""
    await org_svc.add_member(db, cache, org_id, data.user_id, data.org_role)
    return {"message": "Member added successfully"}
