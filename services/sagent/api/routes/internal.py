"""Internal endpoints — called by Cloud Scheduler or admin tools."""

import logging

from fastapi import APIRouter

from schemas.internal import SyncResponse, SyncResultItem, SyncSummary, SyncTrigger

router = APIRouter(prefix="/api/internal")
logger = logging.getLogger(__name__)


@router.post(
    "/sync",
    response_model=SyncResponse,
    summary="RAG sync",
    description="Sync all RAG corpora from their source folders.",
)
async def internal_sync(trigger: SyncTrigger | None = None):
    """Sync all RAG corpora from their source folders.

    Called by:
    - Cloud Scheduler (every 15 min) with {"trigger": "scheduled"}
    - Manual trigger via `make rag-sync` with {"trigger": "manual"}
    """
    from services.rag.sync import sync_service

    trigger_type = trigger.trigger if trigger else "unknown"
    logger.info(f"RAG sync triggered: {trigger_type}")

    try:
        result = await sync_service.sync_all()
        return SyncResponse(
            success=True,
            trigger=trigger_type,
            summary=SyncSummary(
                total=result.total,
                succeeded=result.succeeded,
                failed=result.failed,
                duration_seconds=round(result.duration_seconds, 2),
            ),
            results=[
                SyncResultItem(
                    team_id=r.team_id,
                    status=r.status.value,
                    file_count=r.file_count,
                    error=r.error,
                    duration_seconds=round(r.duration_seconds, 2)
                    if r.duration_seconds
                    else None,
                )
                for r in result.results
            ],
        )
    except Exception as e:
        logger.exception("RAG sync failed")
        return SyncResponse(success=False, trigger=trigger_type, error=str(e))

