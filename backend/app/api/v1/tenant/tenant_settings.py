"""
Tenant API — Organization Settings (permission-gated).
Router is thin — delegates all logic to org_svc.
"""
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_permission
from app.common.types import CurrentUser
from app.common.constants import Timezone
from app.schemas.organization import TenantOrgUpdate, OrgResponse
from app.schemas.common import SuccessResponse
from app.cache.service import CacheService
from app.services.organization import org_svc
from app.services.audit import audit_svc

router = APIRouter(prefix="/settings", tags=["tenant-settings"])


@router.get("", response_model=OrgResponse)
async def get_org_settings(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("organization.view")),
):
    """Get current organization info."""
    return await org_svc.get(db, cache, user.org_id)


@router.patch("", response_model=OrgResponse)
async def update_org_settings(
    data: TenantOrgUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("organization.update")),
):
    """Update organization name and/or timezone."""
    org = await org_svc.update(db, cache, user.org_id, **data.model_dump(exclude_unset=True))
    await audit_svc.log_action(
        db, user_id=user.user_id, org_id=user.org_id,
        action="update", resource_type="organization",
        resource_id=str(org.id),
        new_values=data.model_dump(exclude_unset=True),
    )
    return org


@router.post("/logo", response_model=SuccessResponse)
async def upload_org_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("organization.update")),
):
    """Upload organization logo/avatar."""
    logo_url = await org_svc.upload_logo(db, cache, user.org_id, file)
    await audit_svc.log_action(
        db, user_id=user.user_id, org_id=user.org_id,
        action="update", resource_type="organization",
        resource_id=user.org_id,
        new_values={"logo_url": logo_url},
    )
    return {"message": "Logo uploaded successfully", "data": {"logo_url": logo_url}}


@router.get("/timezones")
async def list_timezones(
    user: CurrentUser = Depends(require_permission("organization.view")),
):
    """Return list of supported timezones for organization settings."""
    return Timezone.ALL
