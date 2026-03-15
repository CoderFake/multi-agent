"""
Tenant Knowledge API — folder CRUD, document upload/delete, agent knowledge sources.
Router = thin delegation layer. All logic in knowledge_svc.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_cache_service, get_redis, require_permission, require_document_access
from app.common.types import CurrentUser
from app.cache.service import CacheService
from app.schemas.knowledge import (
    FolderCreate, FolderUpdate, DocumentAccessCreate, AgentKnowledgeCreate,
)
from app.services.knowledge import knowledge_svc
from app.services.audit import audit_svc

router = APIRouter(prefix="/knowledge", tags=["tenant-knowledge"])


# ── Folders ──────────────────────────────────────────────────────────────

@router.get("/folders")
async def list_folders(
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("folder.view")),
):
    """List folders in the org."""
    return await knowledge_svc.list_folders(db, cache, user.org_id, user.user_id, user.org_role)


@router.post("/folders", status_code=201)
async def create_folder(
    data: FolderCreate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("folder.create")),
):
    """Create a folder."""
    result = await knowledge_svc.create_folder(
        db, cache, user.org_id, data.name, data.description,
        data.parent_id, data.access_type,
    )
    await audit_svc.log_action(
        db, user.user_id, "create", "folder", result["id"],
        org_id=user.org_id, new_values=data.model_dump(),
    )
    return result


@router.put("/folders/{folder_id}")
async def update_folder(
    folder_id: str,
    data: FolderUpdate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("folder.update")),
):
    """Update a folder."""
    result = await knowledge_svc.update_folder(
        db, cache, user.org_id, folder_id,
        **data.model_dump(exclude_unset=True),
    )
    await audit_svc.log_action(
        db, user.user_id, "update", "folder", folder_id,
        org_id=user.org_id, new_values=data.model_dump(exclude_unset=True),
    )
    return result


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("folder.delete")),
):
    """Delete a folder and its documents."""
    deleted_docs = await knowledge_svc.delete_folder(db, cache, user.org_id, folder_id)
    # Audit folder deletion
    await audit_svc.log_action(
        db, user.user_id, "delete", "folder", folder_id, org_id=user.org_id,
    )
    # Audit each document deletion within the folder
    for doc in deleted_docs:
        await audit_svc.log_action(
            db, user.user_id, "delete", "document", doc["id"],
            org_id=user.org_id,
            new_values={"title": doc["title"], "file_name": doc["file_name"], "via_folder_delete": folder_id},
        )


# ── Folder Access ────────────────────────────────────────────────────────

@router.get("/folders/groups")
async def list_groups_for_access(
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("folder_access.manage")),
):
    """Lightweight groups list for folder access management."""
    return await knowledge_svc.list_groups_for_access(db, user.org_id)

@router.get("/folders/{folder_id}/access")
async def get_folder_access(
    folder_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("folder.view")),
):
    """Get group access for a folder."""
    return await knowledge_svc.get_folder_access(db, folder_id)


@router.post("/folders/{folder_id}/access", status_code=201)
async def set_folder_access(
    folder_id: str,
    data: DocumentAccessCreate,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("folder_access.manage")),
):
    """Set group access for a folder."""
    result = await knowledge_svc.set_folder_access(
        db, cache, user.org_id, folder_id,
        data.group_id, data.can_read, data.can_write,
    )
    await audit_svc.log_action(
        db, user.user_id, "set_access", "folder", folder_id,
        org_id=user.org_id, new_values=data.model_dump(),
    )
    return result


@router.delete("/folders/{folder_id}/access/{group_id}", status_code=204)
async def remove_folder_access(
    folder_id: str,
    group_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("folder_access.manage")),
):
    """Remove group access from a folder."""
    await knowledge_svc.remove_folder_access(db, cache, user.org_id, folder_id, group_id)
    await audit_svc.log_action(
        db, user.user_id, "remove_access", "folder", folder_id,
        org_id=user.org_id, new_values={"group_id": group_id},
    )


# ── Documents ────────────────────────────────────────────────────────────

@router.get("/folders/{folder_id}/documents")
async def list_documents(
    folder_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("document.view")),
):
    """List documents in a folder."""
    return await knowledge_svc.list_documents(db, user.org_id, folder_id, user.user_id, user.org_role)


@router.post("/documents", status_code=201)
async def upload_document(
    title: str = Form(...),
    folder_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    redis: Redis = Depends(get_redis),
    user: CurrentUser = Depends(require_permission("document.upload")),
):
    """Upload a document to a folder and auto-trigger indexing."""
    file_data = await file.read()
    result = await knowledge_svc.upload_document(
        db, cache, user.org_id, folder_id, user.user_id,
        title, file.filename or "untitled", file_data,
        file.content_type or "application/octet-stream",
        redis=redis,
    )
    await audit_svc.log_action(
        db, user.user_id, "upload", "document", result["id"],
        org_id=user.org_id, new_values={"title": title, "folder_id": folder_id, "file_name": file.filename},
    )
    return result


@router.get("/documents/{document_id}/url")
async def get_document_url(
    document_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("document.view")),
    _access: CurrentUser = Depends(require_document_access()),
):
    """Get public URL for viewing/downloading a document."""
    return await knowledge_svc.get_document_url(db, user.org_id, document_id)


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    user: CurrentUser = Depends(require_permission("document.delete")),
):
    """Delete a document (MinIO + DB)."""
    await knowledge_svc.delete_document(db, cache, user.org_id, document_id)
    await audit_svc.log_action(
        db, user.user_id, "delete", "document", document_id, org_id=user.org_id,
    )


# ── Agent Knowledge Sources ─────────────────────────────────────────────

@router.get("/agent-sources/{agent_id}")
async def list_agent_sources(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("document.view")),
):
    """List knowledge sources for an agent."""
    return await knowledge_svc.list_agent_sources(db, user.org_id, agent_id)


@router.post("/agent-sources", status_code=201)
async def add_agent_source(
    data: AgentKnowledgeCreate,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("agent.update")),
):
    """Link folder/document as knowledge source for an agent."""
    result = await knowledge_svc.add_agent_source(
        db, user.org_id, data.agent_id, data.folder_id, data.document_id,
    )
    await audit_svc.log_action(
        db, user.user_id, "create", "agent_knowledge", result["id"],
        org_id=user.org_id, new_values=data.model_dump(),
    )
    return result


@router.delete("/agent-sources/{source_id}", status_code=204)
async def remove_agent_source(
    source_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("agent.update")),
):
    """Remove agent knowledge source."""
    await knowledge_svc.remove_agent_source(db, user.org_id, source_id)
    await audit_svc.log_action(
        db, user.user_id, "delete", "agent_knowledge", source_id, org_id=user.org_id,
    )
