"""
Seed data for CMS: content types, permissions, and default group templates.
Run: uv run python -m app.init_db
"""
import asyncio
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import db_manager
from app.models.permission import CmsContentType, CmsPermission
from app.models.group import CmsGroup, cms_group_permissions
from app.models.user import CmsUser
from app.utils.hasher import hash_password
from app.utils.datetime_utils import now
from app.utils.logging import get_logger
from app.config.settings import settings

logger = get_logger(__name__)

# ── Content types + permissions to seed ───────────────────────────────

CONTENT_TYPES = [
    ("cms", "user"),
    ("cms", "organization"),
    ("cms", "group"),
    ("cms", "agent"),
    ("cms", "mcp_server"),
    ("cms", "tool"),
    ("cms", "provider"),
    ("cms", "provider_key"),
    ("cms", "folder"),
    ("cms", "document"),
    ("cms", "permission"),
    ("cms", "audit_log"),
    ("cms", "system_setting"),
]

# Standard CRUD permissions per content type
ACTIONS = ["view", "add", "change", "delete"]

# ── Default group templates (system-level, org_id=NULL) ───────────────

DEFAULT_GROUPS = {
    "Org Owner": {
        "description": "Full access to all organization resources",
        "permissions": "*",  # all permissions
    },
    "Org Admin": {
        "description": "Admin access, cannot delete organization",
        "permissions": "*",  # all for now, restrict specific ones later
    },
    "Org Member": {
        "description": "Standard member access",
        "permissions": [
            "view_user", "view_organization", "view_group",
            "view_agent", "view_mcp_server", "view_tool",
            "view_provider", "view_folder", "view_document",
        ],
    },
    "Read Only": {
        "description": "View-only access to all resources",
        "permissions": [p for ct in CONTENT_TYPES for p in [f"view_{ct[1]}"]],
    },
}


async def seed_content_types_and_permissions(db: AsyncSession) -> dict[str, uuid.UUID]:
    """Seed content types and CRUD permissions. Returns codename→id mapping."""
    perm_map: dict[str, uuid.UUID] = {}

    for app_label, model in CONTENT_TYPES:
        # Upsert content type
        result = await db.execute(
            select(CmsContentType).where(
                CmsContentType.app_label == app_label,
                CmsContentType.model == model,
            )
        )
        ct = result.scalar_one_or_none()
        if not ct:
            ct = CmsContentType(app_label=app_label, model=model)
            db.add(ct)
            await db.flush()

        # Create CRUD permissions
        for action in ACTIONS:
            codename = f"{action}_{model}"
            name = f"Can {action} {model.replace('_', ' ')}"

            result = await db.execute(
                select(CmsPermission).where(CmsPermission.codename == codename)
            )
            perm = result.scalar_one_or_none()
            if not perm:
                perm = CmsPermission(
                    content_type_id=ct.id,
                    codename=codename,
                    name=name,
                )
                db.add(perm)
                await db.flush()

            perm_map[codename] = perm.id

    await db.commit()
    logger.info(f"Seeded {len(CONTENT_TYPES)} content types, {len(perm_map)} permissions")
    return perm_map


async def seed_default_groups(db: AsyncSession, perm_map: dict[str, uuid.UUID]) -> None:
    """Seed default group templates with permission assignments."""
    current_time = now()

    for group_name, config in DEFAULT_GROUPS.items():
        result = await db.execute(
            select(CmsGroup).where(
                CmsGroup.name == group_name,
                CmsGroup.org_id.is_(None),
                CmsGroup.is_system_default.is_(True),
            )
        )
        group = result.scalar_one_or_none()
        if not group:
            group = CmsGroup(
                org_id=None,
                name=group_name,
                description=config["description"],
                is_system_default=True,
                created_at=current_time,
            )
            db.add(group)
            await db.flush()

        # Assign permissions
        if config["permissions"] == "*":
            perm_ids = list(perm_map.values())
        else:
            perm_ids = [perm_map[p] for p in config["permissions"] if p in perm_map]

        for perm_id in perm_ids:
            # Check if exists
            result = await db.execute(
                select(cms_group_permissions).where(
                    cms_group_permissions.c.group_id == group.id,
                    cms_group_permissions.c.permission_id == perm_id,
                )
            )
            if not result.first():
                await db.execute(
                    cms_group_permissions.insert().values(
                        group_id=group.id,
                        permission_id=perm_id,
                    )
                )

    await db.commit()
    logger.info(f"Seeded {len(DEFAULT_GROUPS)} default groups")


async def seed_superuser(db: AsyncSession) -> None:
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


async def init_db() -> None:
    """Run all seed operations."""
    await db_manager.connect()

    try:
        async for db in db_manager.get_session():
            perm_map = await seed_content_types_and_permissions(db)
            await seed_default_groups(db, perm_map)
            await seed_superuser(db)
            logger.info("Database initialization complete!")
            break
    finally:
        await db_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(init_db())
