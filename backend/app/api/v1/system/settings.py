"""
System API — Settings key-value management (superuser only).
Thin router — all logic in setting_svc, schemas in schemas/system_setting.py.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, require_superuser
from app.common.types import CurrentUser
from app.schemas.system_setting import SettingResponse, SettingUpdate
from app.cache.service import CacheService
from app.services.system_setting import setting_svc
from app.services.audit import audit_svc

router = APIRouter(prefix="/settings", tags=["system-settings"])


@router.get("", response_model=list[SettingResponse])
async def list_settings(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """List all system settings."""
    return await setting_svc.list_all(db, cache)


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Get a setting by key."""
    return await setting_svc.get_by_key(db, cache, key)


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    data: SettingUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_superuser),
):
    """Create or update a setting."""
    new_data, old_values = await setting_svc.upsert(db, cache, key, data.value, data.description)
    await audit_svc.log_action(
        db, user.user_id, "update", "system_setting", new_data["id"],
        old_values=old_values, new_values={"value": data.value},
    )
    return new_data
