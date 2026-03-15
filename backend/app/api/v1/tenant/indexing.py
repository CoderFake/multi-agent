"""
Tenant Indexing API — submit indexing jobs, list active tasks, SSE progress stream.

Router = thin delegation layer. All logic in indexing_svc.
Rules: router thin (rule #11), service singleton (rule #15).
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_redis, require_permission
from app.common.types import CurrentUser
from app.schemas.indexing import IndexJobSubmit, IndexJobResponse
from app.services.indexing import indexing_svc

router = APIRouter(prefix="/knowledge/indexing", tags=["tenant-indexing"])


@router.post("/documents/{document_id}/index", response_model=IndexJobResponse)
async def submit_indexing_job(
    document_id: str,
    data: IndexJobSubmit = IndexJobSubmit(),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    user: CurrentUser = Depends(require_permission("document.index")),
):
    """Submit a document for indexing. Creates job and pushes to Redis queue."""
    try:
        return await indexing_svc.submit_job(
            db, redis, user.org_id, document_id, data.agent_code,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/tasks")
async def list_active_tasks(
    db: AsyncSession = Depends(get_db_session),
    user: CurrentUser = Depends(require_permission("document.view")),
):
    """List active/running indexing jobs for this org."""
    return await indexing_svc.list_active_jobs(db, user.org_id)


@router.get("/{job_id}/progress")
async def stream_progress(
    job_id: str,
    redis: Redis = Depends(get_redis),
    user: CurrentUser = Depends(require_permission("document.view")),
):
    """SSE stream of indexing progress. Polls Redis every 1s."""
    return StreamingResponse(
        indexing_svc.stream_progress(redis, job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{job_id}/sync", status_code=204)
async def sync_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    user: CurrentUser = Depends(require_permission("document.index")),
):
    """Sync job status from Redis back to DB. Called when SSE completes."""
    await indexing_svc.sync_job_status(db, redis, job_id)
