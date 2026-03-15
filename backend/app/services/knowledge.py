"""
Knowledge service — folder CRUD, document upload/delete, agent knowledge sources.
Business logic only; routes delegate here.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_, or_, delete, exists
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.cache.invalidation import CacheInvalidation
from app.cache.keys import CacheKeys
from app.cache.service import CacheService
from app.common.constants import ErrorCode
from app.config.settings import settings
from app.core.exceptions import CmsException
from app.models.folder import CmsFolder
from app.models.group import CmsGroup
from app.models.document import CmsDocument, CmsDocumentAccess, CmsAgentKnowledge
from app.models.group import cms_user_groups
from app.models.document import CmsKnowledgeIndexJob
from app.utils.storage import upload_file_bytes, delete_file, generate_path, get_public_url
from app.utils.logging import get_logger

logger = get_logger(__name__)


class KnowledgeService:
    """Folder CRUD, document management, agent knowledge source linking."""

    # ── Folder CRUD ──────────────────────────────────────────────────────

    async def list_folders(
        self, db: AsyncSession, cache: CacheService, org_id: str,
        user_id: str | None = None, org_role: str | None = None,
    ) -> list[dict]:
        """List folders in an org, filtering restricted folders by user access.
        Owner/admin/superuser see all folders.
        Other users only see public + restricted folders they have group access to.
        """

        async def _fetch():
            result = await db.execute(
                select(
                    CmsFolder,
                    func.count(CmsDocument.id).label("doc_count"),
                )
                .outerjoin(CmsDocument, CmsDocument.folder_id == CmsFolder.id)
                .where(CmsFolder.org_id == org_id)
                .group_by(CmsFolder.id)
                .order_by(CmsFolder.sort_order, CmsFolder.name)
            )
            return [
                {
                    "id": str(row.CmsFolder.id),
                    "org_id": str(row.CmsFolder.org_id),
                    "parent_id": str(row.CmsFolder.parent_id) if row.CmsFolder.parent_id else None,
                    "name": row.CmsFolder.name,
                    "description": row.CmsFolder.description,
                    "access_type": row.CmsFolder.access_type,
                    "sort_order": row.CmsFolder.sort_order,
                    "created_at": row.CmsFolder.created_at,
                    "document_count": row.doc_count,
                }
                for row in result.all()
            ]

        all_folders = await cache.get_or_set(
            CacheKeys.org_folders(org_id), _fetch,
            ttl=settings.CACHE_DEFAULT_TTL,
        ) or []

        if org_role in ("owner", "admin") or not user_id:
            return all_folders

        accessible_result = await db.execute(
            select(CmsDocumentAccess.folder_id).where(
                CmsDocumentAccess.can_read == True,  # noqa: E712
                CmsDocumentAccess.group_id.in_(
                    select(cms_user_groups.c.group_id).where(
                        cms_user_groups.c.user_id == user_id,
                    )
                ),
            )
        )
        accessible_ids = {str(r[0]) for r in accessible_result.all()}

        return [
            f for f in all_folders
            if f["access_type"] == "public" or f["id"] in accessible_ids
        ]

    async def create_folder(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, name: str, description: str | None = None,
        parent_id: str | None = None, access_type: str = "public",
    ) -> dict:
        """Create a folder."""
        now = datetime.now(timezone.utc)
        folder = CmsFolder(
            org_id=org_id, parent_id=parent_id, name=name,
            description=description, access_type=access_type,
            sort_order=0, created_at=now,
        )
        db.add(folder)
        await db.commit()
        await db.refresh(folder)

        await CacheInvalidation(cache).clear_org_folders(org_id)

        return {
            "id": str(folder.id), "org_id": str(folder.org_id),
            "parent_id": str(folder.parent_id) if folder.parent_id else None,
            "name": folder.name, "description": folder.description,
            "access_type": folder.access_type, "sort_order": folder.sort_order,
            "created_at": folder.created_at, "document_count": 0,
        }

    async def update_folder(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, folder_id: str, **data,
    ) -> dict:
        """Update a folder."""
        folder = await db.get(CmsFolder, folder_id)
        if not folder or str(folder.org_id) != org_id:
            raise CmsException(error_code="FOLDER_NOT_FOUND", detail="Folder not found", status_code=404)

        for k, v in data.items():
            if v is not None:
                setattr(folder, k, v)
        await db.commit()
        await db.refresh(folder)

        await CacheInvalidation(cache).clear_org_folders(org_id)

        doc_count = await db.scalar(
            select(func.count(CmsDocument.id)).where(CmsDocument.folder_id == folder_id)
        ) or 0

        return {
            "id": str(folder.id), "org_id": str(folder.org_id),
            "parent_id": str(folder.parent_id) if folder.parent_id else None,
            "name": folder.name, "description": folder.description,
            "access_type": folder.access_type, "sort_order": folder.sort_order,
            "created_at": folder.created_at, "document_count": doc_count,
        }

    async def delete_folder(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, folder_id: str,
    ) -> list[dict]:
        """Delete a folder and all its documents. Returns deleted doc info for audit logging."""
        folder = await db.get(CmsFolder, folder_id)
        if not folder or str(folder.org_id) != org_id:
            raise CmsException(error_code="FOLDER_NOT_FOUND", detail="Folder not found", status_code=404)

        # Collect document info for audit, then delete from storage
        docs_result = await db.execute(
            select(CmsDocument).where(CmsDocument.folder_id == folder_id)
        )
        deleted_docs = []
        for doc in docs_result.scalars().all():
            deleted_docs.append({
                "id": str(doc.id),
                "title": doc.title,
                "file_name": doc.file_name,
            })
            try:
                await delete_file(doc.storage_path)
            except Exception as e:
                logger.warning(f"Failed to delete file {doc.storage_path}: {e}")

        await db.delete(folder)
        await db.commit()

        await CacheInvalidation(cache).clear_org_folders(org_id)

        return deleted_docs

    # ── Folder Access ────────────────────────────────────────────────────

    async def list_groups_for_access(self, db: AsyncSession, org_id: str) -> list[dict]:
        """Lightweight group list for folder access management."""
        from app.models.group import CmsGroup
        result = await db.execute(
            select(CmsGroup.id, CmsGroup.name)
            .where(CmsGroup.org_id == org_id)
            .order_by(CmsGroup.name)
        )
        return [{"id": str(row.id), "name": row.name} for row in result.all()]

    async def get_folder_access(self, db: AsyncSession, folder_id: str) -> list[dict]:
        """Get group access for a folder, including group names."""
        result = await db.execute(
            select(CmsDocumentAccess, CmsGroup.name.label("group_name"))
            .outerjoin(CmsGroup, CmsGroup.id == CmsDocumentAccess.group_id)
            .where(CmsDocumentAccess.folder_id == folder_id)
        )
        return [
            {
                "id": str(row.CmsDocumentAccess.id),
                "folder_id": str(row.CmsDocumentAccess.folder_id),
                "group_id": str(row.CmsDocumentAccess.group_id),
                "group_name": row.group_name or str(row.CmsDocumentAccess.group_id),
                "can_read": row.CmsDocumentAccess.can_read,
                "can_write": row.CmsDocumentAccess.can_write,
            }
            for row in result.all()
        ]

    async def set_folder_access(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, folder_id: str, group_id: str,
        can_read: bool = True, can_write: bool = False,
    ) -> dict:
        """Set group access for a folder."""
        # Check existing
        existing = await db.execute(
            select(CmsDocumentAccess).where(
                CmsDocumentAccess.folder_id == folder_id,
                CmsDocumentAccess.group_id == group_id,
            )
        )
        access = existing.scalar_one_or_none()

        if access:
            access.can_read = can_read
            access.can_write = can_write
        else:
            access = CmsDocumentAccess(
                folder_id=folder_id, group_id=group_id,
                can_read=can_read, can_write=can_write,
            )
            db.add(access)

        await db.commit()
        await db.refresh(access)

        return {
            "id": str(access.id), "folder_id": str(access.folder_id),
            "group_id": str(access.group_id),
            "can_read": access.can_read, "can_write": access.can_write,
        }

    async def remove_folder_access(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, folder_id: str, group_id: str,
    ) -> None:
        """Remove group access from a folder."""
        await db.execute(
            delete(CmsDocumentAccess).where(
                CmsDocumentAccess.folder_id == folder_id,
                CmsDocumentAccess.group_id == group_id,
            )
        )
        await db.commit()

    # ── Document CRUD ────────────────────────────────────────────────────

    async def list_documents(
        self, db: AsyncSession, org_id: str, folder_id: str,
        user_id: str | None = None, org_role: str | None = None,
    ) -> list[dict]:
        """List documents in a folder. Returns empty if user has no access to restricted folder."""
        if org_role not in ("owner", "admin") and user_id:
            folder = await db.get(CmsFolder, folder_id)
            if folder and folder.access_type == "restricted":
                has_access = await db.scalar(
                    select(exists().where(
                        and_(
                            CmsDocumentAccess.folder_id == folder_id,
                            CmsDocumentAccess.can_read == True,  # noqa: E712
                            CmsDocumentAccess.group_id.in_(
                                select(cms_user_groups.c.group_id).where(
                                    cms_user_groups.c.user_id == user_id,
                                )
                            ),
                        )
                    ))
                )
                if not has_access:
                    return []

        result = await db.execute(
            select(CmsDocument)
            .where(CmsDocument.org_id == org_id, CmsDocument.folder_id == folder_id)
            .order_by(CmsDocument.created_at.desc())
        )
        return [
            {
                "id": str(d.id), "org_id": str(d.org_id),
                "folder_id": str(d.folder_id),
                "uploaded_by": str(d.uploaded_by) if d.uploaded_by else None,
                "title": d.title, "file_name": d.file_name,
                "file_type": d.file_type, "file_size": d.file_size,
                "access_type": d.access_type, "index_status": d.index_status,
                "chunk_count": d.chunk_count, "indexed_at": d.indexed_at,
                "created_at": d.created_at, "updated_at": d.updated_at,
            }
            for d in result.scalars().all()
        ]

    async def upload_document(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, folder_id: str, user_id: str,
        title: str, file_name: str, file_data: bytes, content_type: str,
        redis: Redis | None = None,
    ) -> dict:
        """Upload a document to a folder (MinIO + DB)."""
        # Validate folder
        folder = await db.get(CmsFolder, folder_id)
        if not folder or str(folder.org_id) != org_id:
            raise CmsException(error_code="FOLDER_NOT_FOUND", detail="Folder not found", status_code=404)

        # Determine file type from extension
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "unknown"
        file_size = len(file_data)

        # Upload to MinIO
        path = generate_path(f"orgs/{org_id}/{folder_id}", file_name)
        storage_path = await upload_file_bytes(
            file_data, path, content_type=content_type,
        )

        now = datetime.now(timezone.utc)
        doc = CmsDocument(
            org_id=org_id, folder_id=folder_id, uploaded_by=user_id,
            title=title, file_name=file_name, file_type=ext,
            file_size=file_size, storage_path=storage_path,
            access_type=folder.access_type,  # inherit from folder
            index_status="pending", chunk_count=0,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        await CacheInvalidation(cache).clear_org_folders(org_id)

        result = {
            "id": str(doc.id), "org_id": str(doc.org_id),
            "folder_id": str(doc.folder_id),
            "uploaded_by": str(doc.uploaded_by) if doc.uploaded_by else None,
            "title": doc.title, "file_name": doc.file_name,
            "file_type": doc.file_type, "file_size": doc.file_size,
            "access_type": doc.access_type, "index_status": doc.index_status,
            "chunk_count": doc.chunk_count, "indexed_at": None,
            "created_at": doc.created_at, "updated_at": doc.updated_at,
        }

        if redis is not None:
            try:
                from app.services.indexing import indexing_svc
                await indexing_svc.submit_job(
                    db, redis, org_id, str(doc.id),
                )
                result["index_status"] = "indexing"
                logger.info("Auto-triggered indexing for document %s", doc.id)
            except Exception as e:
                logger.warning("Failed to auto-trigger indexing for %s: %s", doc.id, e)

        return result

    async def get_document_url(
        self, db: AsyncSession, org_id: str, document_id: str,
    ) -> dict:
        """Get public URL for viewing/downloading a document."""
        doc = await db.get(CmsDocument, document_id)
        if not doc or str(doc.org_id) != org_id:
            raise CmsException(error_code="DOCUMENT_NOT_FOUND", detail="Document not found", status_code=404)

        url = get_public_url(doc.storage_path)
        return {
            "id": str(doc.id),
            "file_name": doc.file_name,
            "file_type": doc.file_type,
            "content_type": f"application/{doc.file_type}" if doc.file_type not in ("png", "jpg", "jpeg", "gif", "webp") else f"image/{doc.file_type}",
            "url": url,
        }

    async def delete_document(
        self, db: AsyncSession, cache: CacheService,
        org_id: str, document_id: str,
    ) -> None:
        """Delete a document (MinIO + DB)."""
        doc = await db.get(CmsDocument, document_id)
        if not doc or str(doc.org_id) != org_id:
            raise CmsException(error_code="DOCUMENT_NOT_FOUND", detail="Document not found", status_code=404)

        # Delete from MinIO
        try:
            await delete_file(doc.storage_path)
        except Exception as e:
            logger.warning(f"Failed to delete file {doc.storage_path}: {e}")

        await db.delete(doc)
        await db.commit()

        await CacheInvalidation(cache).clear_org_folders(org_id)

    # ── Agent Knowledge Sources ──────────────────────────────────────────

    async def list_agent_sources(self, db: AsyncSession, org_id: str, agent_id: str) -> list[dict]:
        """List knowledge sources (folders/docs) for an agent."""
        result = await db.execute(
            select(CmsAgentKnowledge)
            .where(CmsAgentKnowledge.org_id == org_id, CmsAgentKnowledge.agent_id == agent_id)
        )
        return [
            {
                "id": str(s.id), "org_id": str(s.org_id),
                "agent_id": str(s.agent_id),
                "folder_id": str(s.folder_id) if s.folder_id else None,
                "document_id": str(s.document_id) if s.document_id else None,
                "created_at": s.created_at,
            }
            for s in result.scalars().all()
        ]

    async def add_agent_source(
        self, db: AsyncSession, org_id: str,
        agent_id: str, folder_id: str | None = None, document_id: str | None = None,
    ) -> dict:
        """Link a folder or document as knowledge source for an agent."""
        now = datetime.now(timezone.utc)
        source = CmsAgentKnowledge(
            org_id=org_id, agent_id=agent_id,
            folder_id=folder_id, document_id=document_id,
            created_at=now,
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)

        return {
            "id": str(source.id), "org_id": str(source.org_id),
            "agent_id": str(source.agent_id),
            "folder_id": str(source.folder_id) if source.folder_id else None,
            "document_id": str(source.document_id) if source.document_id else None,
            "created_at": source.created_at,
        }

    async def remove_agent_source(self, db: AsyncSession, org_id: str, source_id: str) -> None:
        """Remove an agent knowledge source."""
        source = await db.get(CmsAgentKnowledge, source_id)
        if not source or str(source.org_id) != org_id:
            raise CmsException(error_code="KNOWLEDGE_SOURCE_NOT_FOUND", detail="Source not found", status_code=404)

        await db.delete(source)
        await db.commit()


# Singleton
knowledge_svc = KnowledgeService()
