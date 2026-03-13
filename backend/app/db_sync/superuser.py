"""
DB Sync: Superuser seeding.
Creates the default superuser if none exists.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import CmsUser
from app.utils.hasher import hash_password
from app.utils.logging import get_logger
from app.config.settings import settings

logger = get_logger(__name__)


async def sync_superuser(db: AsyncSession) -> None:
    """Create a default superuser if none exists."""
    result = await db.execute(
        select(CmsUser).where(CmsUser.is_superuser.is_(True))
    )
    if result.scalar_one_or_none():
        logger.info("Superuser already exists, skipping")
        return

    superuser = CmsUser(
        email=settings.SUPERUSER_EMAIL,
        hashed_password=hash_password(settings.SUPERUSER_PASSWORD),
        full_name=settings.SUPERUSER_FULL_NAME,
        is_superuser=True,
        is_active=True,
    )
    db.add(superuser)
    await db.commit()
    logger.info(f"Created default superuser {settings.SUPERUSER_FULL_NAME}")
