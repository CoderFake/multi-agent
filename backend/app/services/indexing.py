"""
Indexing service — submit indexing jobs, list active jobs, stream progress from Redis.

Rules applied:
  - Service singleton (rule #15)
  - Redis-first (rule #8)
  - TTL tập trung (rule #12 — uses settings)
  - No business logic in routes (rule #11)
"""

import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
from uuid import uuid4

import asyncio
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.document import CmsDocument, CmsKnowledgeIndexJob, CmsDocumentAccess
from app.models.organization import CmsOrganization
from app.cache.keys import CacheKeys
from app.utils.logging import get_logger

logger = get_logger(__name__)


class IndexingService:
    """Manages indexing job lifecycle: submit, list, stream progress."""

    async def submit_job(
        self,
        db: AsyncSession,
        redis: Redis,
        org_id: str,
        document_id: str,
        agent_code: str = "",
    ) -> dict:
        """
        Submit a document for indexing.
        1. Validate document exists and belongs to org
        2. Create CmsKnowledgeIndexJob record
        3. Push task payload to Redis idx:queue
        4. Return job_id
        """
        # Fetch document
        result = await db.execute(
            select(CmsDocument).where(
                CmsDocument.id == document_id,
                CmsDocument.org_id == org_id,
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document {document_id} not found in org {org_id}")

        # Fetch org for subdomain
        org_result = await db.execute(
            select(CmsOrganization).where(CmsOrganization.id == org_id)
        )
        org = org_result.scalar_one_or_none()
        if not org:
            raise ValueError(f"Organization {org_id} not found")

        org_subdomain = org.subdomain or org.slug or str(org.id).replace("-", "")

        # Fetch group_ids for restricted access
        group_ids = []
        if doc.access_type == "restricted":
            access_result = await db.execute(
                select(CmsDocumentAccess.group_id).where(
                    CmsDocumentAccess.document_id == document_id,
                    CmsDocumentAccess.can_read == True,
                )
            )
            group_ids = [str(row[0]) for row in access_result.fetchall()]

            # Also check folder-level access
            if doc.folder_id:
                folder_access_result = await db.execute(
                    select(CmsDocumentAccess.group_id).where(
                        CmsDocumentAccess.folder_id == doc.folder_id,
                        CmsDocumentAccess.can_read == True,
                    )
                )
                folder_groups = [str(row[0]) for row in folder_access_result.fetchall()]
                group_ids = list(set(group_ids + folder_groups))

        # Create index job record
        job_id = str(uuid4())
        now = datetime.now(timezone.utc)

        index_job = CmsKnowledgeIndexJob(
            id=job_id,
            org_id=org_id,
            document_id=document_id,
            status="pending",
            total_chunks=0,
            processed_chunks=0,
            created_at=now,
        )
        db.add(index_job)

        # Update document status
        await db.execute(
            update(CmsDocument)
            .where(CmsDocument.id == document_id)
            .values(index_status="indexing")
        )

        await db.flush()

        # Push task to Redis queue
        task_payload = {
            "job_id": job_id,
            "org_id": str(org_id),
            "org_subdomain": org_subdomain,
            "document_id": str(document_id),
            "folder_id": str(doc.folder_id) if doc.folder_id else "",
            "file_name": doc.file_name,
            "storage_path": doc.storage_path,
            "access_type": doc.access_type or "public",
            "group_ids": group_ids,
            "agent_code": agent_code,
        }
        await redis.lpush(CacheKeys.index_queue(), json.dumps(task_payload))

        logger.info("Indexing job submitted: job=%s doc=%s", job_id, document_id)

        return {
            "job_id": job_id,
            "document_id": str(document_id),
            "status": "pending",
            "message": "Indexing job submitted",
        }

    async def list_active_jobs(
        self,
        db: AsyncSession,
        org_id: str,
    ) -> list[dict]:
        """List active/running indexing jobs for an org."""
        result = await db.execute(
            select(CmsKnowledgeIndexJob)
            .where(
                CmsKnowledgeIndexJob.org_id == org_id,
                CmsKnowledgeIndexJob.status.in_(["pending", "processing"]),
            )
            .order_by(CmsKnowledgeIndexJob.created_at.desc())
        )
        jobs = result.scalars().all()

        return [
            {
                "id": str(job.id),
                "document_id": str(job.document_id),
                "status": job.status,
                "total_chunks": job.total_chunks,
                "processed_chunks": job.processed_chunks,
                "error_message": job.error_message,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "created_at": job.created_at.isoformat() if job.created_at else "",
            }
            for job in jobs
        ]

    async def get_job_progress(
        self,
        redis: Redis,
        job_id: str,
    ) -> Optional[dict]:
        """Get task progress from Redis."""
        key = CacheKeys.index_task(job_id)
        raw = await redis.get(key)
        if raw:
            return json.loads(raw)
        return None

    async def stream_progress(
        self,
        redis: Redis,
        job_id: str,
        poll_interval: float = 1.0,
    ) -> AsyncGenerator[str, None]:
        """
        Async generator that polls Redis for task progress and yields SSE events.
        Stops when status is 'completed' or 'failed'.
        """
        while True:
            progress = await self.get_job_progress(redis, job_id)

            if progress:
                event_data = json.dumps(progress, default=str)
                yield f"data: {event_data}\n\n"

                status = progress.get("status", "")
                if status in ("completed", "failed"):
                    break
            else:
                # No data yet — send heartbeat
                yield f"data: {json.dumps({'job_id': job_id, 'status': 'queued', 'progress': 0, 'message': 'Waiting...'})}\n\n"

            await asyncio.sleep(poll_interval)

    async def sync_job_status(
        self,
        db: AsyncSession,
        redis: Redis,
        job_id: str,
    ) -> None:
        """Sync Redis task progress back to DB (CmsKnowledgeIndexJob + CmsDocument)."""
        progress = await self.get_job_progress(redis, job_id)
        if not progress:
            return

        status = progress.get("status", "")
        db_status = "processing"
        if status == "completed":
            db_status = "completed"
        elif status == "failed":
            db_status = "failed"

        values = {
            "status": db_status,
            "total_chunks": progress.get("total_chunks", 0),
            "processed_chunks": progress.get("processed_chunks", 0),
            "error_message": progress.get("error"),
        }

        if status == "completed":
            values["completed_at"] = datetime.now(timezone.utc)
        elif db_status == "processing" and not progress.get("started_at"):
            values["started_at"] = datetime.now(timezone.utc)

        await db.execute(
            update(CmsKnowledgeIndexJob)
            .where(CmsKnowledgeIndexJob.id == job_id)
            .values(**values)
        )

        # Update document index_status
        doc_id = progress.get("document_id", "")
        if doc_id:
            doc_status = "indexing"
            if status == "completed":
                doc_status = "indexed"
            elif status == "failed":
                doc_status = "failed"

            doc_values = {"index_status": doc_status}
            if status == "completed":
                doc_values["indexed_at"] = datetime.now(timezone.utc)
                doc_values["chunk_count"] = progress.get("total_chunks", 0)

            await db.execute(
                update(CmsDocument)
                .where(CmsDocument.id == doc_id)
                .values(**doc_values)
            )


indexing_svc = IndexingService()
