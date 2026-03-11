"""RAG services for corpus and team management.

These services provide:
- Team membership (which teams a user belongs to)
- Corpus registry (which Milvus collections teams have access to)
- Sync service (dispatches indexing tasks via RabbitMQ to retrieval microservice)

Team-corpus mappings are stored in PostgreSQL via SQLAlchemy ORM.
"""

from services.rag.corpus_registry import CorpusRegistry, corpus_registry
from services.rag.teams import (
    DatabaseTeamService,
    TeamMembershipService,
    get_team_service,
    team_service,
)

__all__ = [
    "CorpusRegistry",
    "corpus_registry",
    "TeamMembershipService",
    "DatabaseTeamService",
    "get_team_service",
    "team_service",
]
