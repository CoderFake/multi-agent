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
# Format: (app_label, model)
# Covers ALL models in app/models/__init__.py

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
    ("cms", "feedback"),
    ("cms", "notification"),
    ("cms", "invite"),
    ("cms", "ui_component"),
]

# ── Permission definitions ────────────────────────────────────────────
# Codename format: resource.action  (e.g. user.view, agent.create)
# This matches what the frontend sidebar + permission service expects.
#
# Special actions beyond CRUD are defined per resource.

PERMISSIONS: dict[str, list[str]] = {
    # Auth & RBAC
    "user":            ["view", "create", "update", "delete", "invite"],
    # Organization — tenant can only view/update their own org
    "organization":    ["view", "update"],
    "group":           ["view", "create", "update", "delete"],
    "permission":      ["view", "assign", "revoke"],
    "invite":          ["view", "create", "revoke", "resend"],

    # Agent & MCP — tenant manages agents; MCP servers are system-level
    "agent":           ["view", "create", "update", "delete", "deploy"],
    "mcp_server":      ["view"],           # view only — MCP servers managed at system level
    "agent_mcp":       ["view", "attach", "detach"],  # attach/detach MCP to agents
    "tool":            ["view"],            # tools are auto-discovered from MCP
    "tool_access":     ["view", "assign", "revoke"],  # enable/disable tools per group
    "ui_component":    ["view", "update"],

    # Provider — tenant uses providers, not create/delete (system-level)
    "provider":        ["view", "update"],
    "provider_key":    ["view", "create", "update", "delete"],

    # Knowledge
    "folder":          ["view", "create", "update", "delete"],
    "document":        ["view", "create", "update", "delete", "upload"],

    # Other
    "audit_log":       ["view", "export"],
    "system_setting":  ["view"],  # tenant can view settings, superuser manages them
    "feedback":        ["view", "create", "delete"],
    "notification":    ["view", "delete"],
}

# Human name template
ACTION_LABELS = {
    "view": "View", "create": "Create", "update": "Update",
    "delete": "Delete", "invite": "Invite", "assign": "Assign",
    "revoke": "Revoke", "resend": "Resend", "deploy": "Deploy",
    "upload": "Upload", "export": "Export",
    "attach": "Attach", "detach": "Detach",
}

# ── Default group templates (system-level, org_id=NULL) ───────────────

# All codenames for owner
ALL_CODENAMES = [
    f"{resource}.{action}"
    for resource, actions in PERMISSIONS.items()
    for action in actions
]

# Admin: everything except destructive org/user ops
ADMIN_EXCLUDED = {
    "organization.delete",
    "user.delete",
}
ADMIN_CODENAMES = [c for c in ALL_CODENAMES if c not in ADMIN_EXCLUDED]

# Member: view everything + basic create/update within their scope
MEMBER_CODENAMES = [
    # View all resources
    *[f"{r}.view" for r in PERMISSIONS],
    # Create/update in their scope
    "agent.create", "agent.update",
    "mcp_server.create", "mcp_server.update",
    "folder.create", "folder.update",
    "document.create", "document.update", "document.upload",
    "feedback.create",
]
# Deduplicate
MEMBER_CODENAMES = list(dict.fromkeys(MEMBER_CODENAMES))

# Read Only: view only
READONLY_CODENAMES = [f"{r}.view" for r in PERMISSIONS]

DEFAULT_GROUPS = {
    "Org Owner": {
        "description": "Full access to all organization resources",
        "codenames": ALL_CODENAMES,
    },
    "Org Admin": {
        "description": "Admin access, cannot delete organization or users",
        "codenames": ADMIN_CODENAMES,
    },
    "Org Member": {
        "description": "Standard member — view all, create/update within scope",
        "codenames": MEMBER_CODENAMES,
    },
    "Read Only": {
        "description": "View-only access to all resources",
        "codenames": READONLY_CODENAMES,
    },
}


async def seed_content_types_and_permissions(db: AsyncSession) -> dict[str, uuid.UUID]:
    """Seed content types and permissions. Returns codename→id mapping."""
    perm_map: dict[str, uuid.UUID] = {}

    # Build content type lookup
    ct_map: dict[str, CmsContentType] = {}
    for app_label, model in CONTENT_TYPES:
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
        ct_map[model] = ct

    # Create permissions
    for resource, actions in PERMISSIONS.items():
        ct = ct_map.get(resource)
        if not ct:
            logger.warning(f"No content type for resource '{resource}', skipping")
            continue

        for action in actions:
            codename = f"{resource}.{action}"
            label = ACTION_LABELS.get(action, action.capitalize())
            name = f"Can {label.lower()} {resource.replace('_', ' ')}"

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
        perm_ids = [perm_map[c] for c in config["codenames"] if c in perm_map]

        for perm_id in perm_ids:
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
