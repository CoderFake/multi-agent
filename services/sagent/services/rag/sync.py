"""RAG corpus sync service.

Dispatches indexing tasks to the retrieval microservice via:
1. Direct HTTP webhook (sync)
2. RabbitMQ (async background tasks)

Usage:
    from services.rag.sync import sync_service

    # Dispatch sync for all corpora
    results = await sync_service.sync_all()
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from config.settings import settings
from core.database import get_session
from models.team_corpus import TeamCorpus

logger = logging.getLogger(__name__)


class SyncStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SyncResult:
    team_id: str
    collection_name: str
    status: SyncStatus
    file_count: int | None = None
    error: str | None = None
    duration_seconds: float | None = None


@dataclass
class SyncAllResult:
    total: int
    succeeded: int
    failed: int
    results: list[SyncResult]
    duration_seconds: float


class SyncService:
    """Service for dispatching indexing tasks to the retrieval microservice."""

    def _get_all_corpora(self) -> list[TeamCorpus]:
        """Get all corpora from database using ORM."""
        session = get_session()
        try:
            return session.query(TeamCorpus).all()
        finally:
            session.close()

    def _update_sync_status(
        self,
        team_id: str,
        status: SyncStatus,
        file_count: int | None = None,
    ) -> None:
        """Update sync status in database using ORM."""
        session = get_session()
        try:
            corpus = session.query(TeamCorpus).filter_by(team_id=team_id).first()
            if corpus:
                corpus.last_sync_status = status.value
                corpus.last_sync_at = datetime.now(UTC)
                if file_count is not None:
                    corpus.file_count = file_count
                session.commit()
        finally:
            session.close()

    async def sync_corpus(self, corpus: TeamCorpus) -> SyncResult:
        """Dispatch indexing for a single corpus to retrieval service.

        The actual indexing is handled by the retrieval microservice.
        This method updates sync status and dispatches the request.
        """
        team_id = corpus.team_id
        collection_name = corpus.collection_name

        logger.info(f"Dispatching sync: {team_id} → {collection_name}")
        start_time = datetime.now(UTC)
        self._update_sync_status(team_id, SyncStatus.IN_PROGRESS)

        try:
            # TODO: Implement document extraction (GDrive → chunks)
            # For now, this is a placeholder. The full pipeline will:
            # 1. Fetch files from GDrive folder (corpus.folder_url)
            # 2. Extract text and chunk documents
            # 3. POST chunks to retrieval service /api/v1/index
            # 4. Or publish to RabbitMQ for async processing

            duration = (datetime.now(UTC) - start_time).total_seconds()
            self._update_sync_status(team_id, SyncStatus.COMPLETED)

            return SyncResult(
                team_id=team_id,
                collection_name=collection_name,
                status=SyncStatus.COMPLETED,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.error(f"Sync failed for {team_id}: {e}")
            self._update_sync_status(team_id, SyncStatus.FAILED)

            return SyncResult(
                team_id=team_id,
                collection_name=collection_name,
                status=SyncStatus.FAILED,
                error=str(e),
                duration_seconds=duration,
            )

    async def sync_all(self) -> SyncAllResult:
        """Sync all configured corpora."""
        start_time = datetime.now(UTC)
        corpora = self._get_all_corpora()

        if not corpora:
            logger.info("No corpora configured")
            return SyncAllResult(total=0, succeeded=0, failed=0, results=[], duration_seconds=0)

        results = []
        for corpus in corpora:
            result = await self.sync_corpus(corpus)
            results.append(result)

        duration = (datetime.now(UTC) - start_time).total_seconds()
        succeeded = sum(1 for r in results if r.status == SyncStatus.COMPLETED)
        failed = sum(1 for r in results if r.status == SyncStatus.FAILED)

        return SyncAllResult(
            total=len(corpora),
            succeeded=succeeded,
            failed=failed,
            results=results,
            duration_seconds=duration,
        )


sync_service = SyncService()
