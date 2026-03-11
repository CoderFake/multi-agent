"""Team corpus registry model.

Maps teams to their vector collections in Milvus (replacing Vertex AI RAG corpora).
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class TeamCorpus(Base):
    """Team corpus registry.

    Each team has one corpus (vector collection) in Milvus.
    Tracks sync status for Google Drive → Milvus indexing pipeline.

    Cache keys (future Redis):
        - team_corpus:{team_id} → corpus details
        - team_corpus_by_domain:{email_domain} → team_id lookup
    """

    __tablename__ = "team_corpora"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    team_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    collection_name: Mapped[str] = mapped_column(String, nullable=False)  # Milvus collection
    source_type: Mapped[str] = mapped_column(String, nullable=False)  # 'gdrive'
    folder_url: Mapped[str] = mapped_column(String, nullable=False)
    email_domain: Mapped[str | None] = mapped_column(String)  # e.g. 'example.com'
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_status: Mapped[str | None] = mapped_column(String)  # pending|in_progress|completed|failed
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("team_corpora_team_id_idx", "team_id"),
        Index("team_corpora_email_domain_idx", "email_domain"),
    )

    def __repr__(self) -> str:
        return f"<TeamCorpus team={self.team_id} collection={self.collection_name}>"

    # ── Cache helpers (future Redis) ─────────────────────────────────
    @staticmethod
    def cache_key(team_id: str) -> str:
        return f"team_corpus:{team_id}"

    @staticmethod
    def cache_key_by_domain(email_domain: str) -> str:
        return f"team_corpus_by_domain:{email_domain.lower()}"

