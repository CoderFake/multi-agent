"""
DB Sync: Permissions & Default Groups.
Syncs content types, permissions, and default group templates.
Safe to run repeatedly — idempotent upsert + cleanup of stale entries.
"""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import CmsContentType, CmsPermission
from app.models.group import CmsGroup, cms_group_permissions
from app.utils.datetime_utils import now
from app.utils.logging import get_logger

logger = get_logger(__name__)

# ── Content types to seed ─────────────────────────────────────────────
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
    ("cms", "agent_mcp"),
    ("cms", "tool_access"),
]

# ── Permission definitions ────────────────────────────────────────────
# Codename format: resource.action  (e.g. user.view, agent.create)

PERMISSIONS: dict[str, list[str]] = {
    # Auth & RBAC
    "user":            ["view", "create", "update", "delete", "invite"],
    "organization":    ["view", "update"],
    "group":           ["view", "create", "update", "delete"],
    "permission":      ["view", "assign", "revoke"],
    "invite":          ["view", "create", "revoke", "resend"],

    # Agent & MCP
    "agent":           ["view", "create", "update", "delete", "deploy"],
    "mcp_server":      ["view"],
    "agent_mcp":       ["view", "assign", "revoke"],
    "tool":            ["view"],
    "tool_access":     ["view", "assign", "revoke"],
    "ui_component":    ["view", "update"],

    # Provider
    "provider":        ["view", "update"],
    "provider_key":    ["view", "create", "update", "delete"],

    # Knowledge
    "folder":          ["view", "create", "update", "delete"],
    "document":        ["view", "create", "update", "delete", "upload"],

    # Other
    "audit_log":       ["view", "export"],
    "system_setting":  ["view"],
    "feedback":        ["view", "create", "delete"],
    "notification":    ["view", "delete"],
}

# Human name template
ACTION_LABELS = {
    "view": "View", "create": "Create", "update": "Update",
    "delete": "Delete", "invite": "Invite", "assign": "Assign",
    "revoke": "Revoke", "resend": "Resend", "deploy": "Deploy",
    "upload": "Upload", "export": "Export",
}

# ── Default group templates (system-level, org_id=NULL) ───────────────

ALL_CODENAMES = [
    f"{resource}.{action}"
    for resource, actions in PERMISSIONS.items()
    for action in actions
]

ADMIN_EXCLUDED = {
    "organization.delete",
    "user.delete",
}
ADMIN_CODENAMES = [c for c in ALL_CODENAMES if c not in ADMIN_EXCLUDED]

MEMBER_CODENAMES = list(dict.fromkeys([
    *[f"{r}.view" for r in PERMISSIONS],
    "agent.create", "agent.update",
    "folder.create", "folder.update",
    "document.create", "document.update", "document.upload",
    "feedback.create",
]))

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


# ── Sync functions ────────────────────────────────────────────────────

async def sync_permissions(db: AsyncSession) -> dict[str, uuid.UUID]:
    """
    Sync content types and permissions with the PERMISSIONS dict.
    - Adds missing content types and permissions
    - Removes deprecated permissions no longer in PERMISSIONS
    - Removes orphaned content types no longer in CONTENT_TYPES
    Safe to run repeatedly — never drops user data beyond stale permissions.
    """
    perm_map: dict[str, uuid.UUID] = {}

    # 1. Sync content types
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
            logger.info(f"  + ContentType: {app_label}.{model}")
        ct_map[model] = ct

    # Remove content types no longer in CONTENT_TYPES
    expected_models = {model for _, model in CONTENT_TYPES}
    all_ct_result = await db.execute(select(CmsContentType))
    for ct in all_ct_result.scalars().all():
        if ct.model not in expected_models:
            await db.delete(ct)
            logger.info(f"  - ContentType removed: {ct.app_label}.{ct.model}")

    # 2. Sync permissions
    expected_codenames: set[str] = set()
    added, updated = 0, 0

    for resource, actions in PERMISSIONS.items():
        ct = ct_map.get(resource)
        if not ct:
            logger.warning(f"No content type for resource '{resource}', skipping")
            continue

        for action in actions:
            codename = f"{resource}.{action}"
            expected_codenames.add(codename)
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
                added += 1
                logger.info(f"  + Permission: {codename}")
            else:
                changed = False
                if perm.name != name:
                    perm.name = name
                    changed = True
                if perm.content_type_id != ct.id:
                    perm.content_type_id = ct.id
                    changed = True
                if changed:
                    updated += 1
                    logger.info(f"  ~ Permission updated: {codename}")

            perm_map[codename] = perm.id

    # Remove permissions no longer in PERMISSIONS dict
    all_perms_result = await db.execute(select(CmsPermission))
    removed = 0
    for perm in all_perms_result.scalars().all():
        if perm.codename not in expected_codenames:
            await db.execute(
                cms_group_permissions.delete().where(
                    cms_group_permissions.c.permission_id == perm.id,
                )
            )
            await db.delete(perm)
            removed += 1
            logger.info(f"  - Permission removed: {perm.codename}")

    await db.commit()
    logger.info(
        f"Permissions synced: {len(perm_map)} total, "
        f"{added} added, {updated} updated, {removed} removed"
    )
    return perm_map


async def sync_default_groups(db: AsyncSession, perm_map: dict[str, uuid.UUID]) -> None:
    """
    Sync default group templates with permission assignments.
    - Creates missing groups
    - Adds missing permission assignments
    - Removes permission assignments no longer in the template
    Safe to run repeatedly without losing org-level groups.
    """
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
            logger.info(f"  + Group: {group_name}")

        # Desired permission IDs for this group
        desired_perm_ids = {perm_map[c] for c in config["codenames"] if c in perm_map}

        # Current permission IDs in DB
        current_result = await db.execute(
            select(cms_group_permissions.c.permission_id).where(
                cms_group_permissions.c.group_id == group.id,
            )
        )
        current_perm_ids = {row[0] for row in current_result.all()}

        # Add missing
        to_add = desired_perm_ids - current_perm_ids
        for perm_id in to_add:
            await db.execute(
                cms_group_permissions.insert().values(
                    group_id=group.id,
                    permission_id=perm_id,
                )
            )

        # Remove stale
        to_remove = current_perm_ids - desired_perm_ids
        for perm_id in to_remove:
            await db.execute(
                cms_group_permissions.delete().where(
                    cms_group_permissions.c.group_id == group.id,
                    cms_group_permissions.c.permission_id == perm_id,
                )
            )

        if to_add or to_remove:
            logger.info(
                f"  ~ Group '{group_name}': +{len(to_add)} / -{len(to_remove)} permissions"
            )

    await db.commit()
    logger.info(f"Synced {len(DEFAULT_GROUPS)} default groups")
