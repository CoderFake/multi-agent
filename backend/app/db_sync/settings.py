"""
System settings seed — default global configuration keys.
Only inserts if key doesn't exist. Run via init_db.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_setting import CmsSystemSetting
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ── Default Settings ────────────────────────────────────────────────────

DEFAULT_SETTINGS: list[dict] = [
    {
        "key": "site_name",
        "value": "Multi-Agent CMS",
        "description": "Tên hiển thị hệ thống",
    },
    {
        "key": "max_orgs_per_user",
        "value": 5,
        "description": "Số tổ chức tối đa mỗi người dùng có thể tạo",
    },
    {
        "key": "max_agents_per_org",
        "value": 20,
        "description": "Số agent tối đa mỗi tổ chức",
    },
    {
        "key": "max_file_upload_mb",
        "value": 50,
        "description": "Giới hạn kích thước file upload (MB)",
    },
    {
        "key": "default_model",
        "value": "gemini-2.5-flash",
        "description": "Model mặc định cho agent mới",
    },
    {
        "key": "rate_limit_requests_per_minute",
        "value": 60,
        "description": "Giới hạn request/phút cho mỗi user",
    },
    {
        "key": "session_timeout_minutes",
        "value": 30,
        "description": "Thời gian timeout phiên đăng nhập (phút)",
    },
    {
        "key": "allow_user_registration",
        "value": False,
        "description": "Cho phép đăng ký tài khoản mới (chỉ qua invite nếu tắt)",
    },
    {
        "key": "maintenance_mode",
        "value": False,
        "description": "Bật chế độ bảo trì hệ thống",
    },
    {
        "key": "default_language",
        "value": "vi",
        "description": "Ngôn ngữ mặc định hệ thống",
    },
]


async def sync_settings(db: AsyncSession) -> None:
    """Seed default system settings. Only inserts if key doesn't exist."""
    now = datetime.now(timezone.utc)
    created = 0

    for sdef in DEFAULT_SETTINGS:
        result = await db.execute(
            select(CmsSystemSetting).where(CmsSystemSetting.key == sdef["key"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            continue

        setting = CmsSystemSetting(
            key=sdef["key"],
            value=sdef["value"],
            description=sdef.get("description"),
            updated_at=now,
        )
        db.add(setting)
        created += 1

    await db.commit()
    logger.info(f"System settings sync: {created} created, {len(DEFAULT_SETTINGS) - created} already existed")
