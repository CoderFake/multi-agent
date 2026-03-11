"""Corpus registry service for team RAG corpora (read-only).

Provides read-only access to team-corpus mappings via ORM.
Returns Milvus collection names for the user's teams.

Usage:
    from services.rag import corpus_registry

    # Get Milvus collection names for user's teams
    collections = corpus_registry.get_collection_names_for_teams(team_ids)
"""

import logging

from core.database import get_session
from models.team_corpus import TeamCorpus

logger = logging.getLogger(__name__)


class CorpusRegistry:
    """Read-only registry for team RAG corpora (Milvus collections).

    Provides methods to query team-corpus mappings via ORM.
    """

    def get_collection_names_for_teams(self, team_ids: list[str]) -> list[str]:
        """Get Milvus collection names for teams.

        Args:
            team_ids: List of team identifiers.

        Returns:
            List of Milvus collection names.
        """
        if not team_ids:
            return []

        session = get_session()
        try:
            corpora = (
                session.query(TeamCorpus.collection_name)
                .filter(TeamCorpus.team_id.in_(team_ids))
                .all()
            )
            return [c.collection_name for c in corpora]
        finally:
            session.close()

    # Keep backward compat alias
    def get_corpus_names_for_teams(self, team_ids: list[str]) -> list[str]:
        """Alias for get_collection_names_for_teams (backward compat)."""
        return self.get_collection_names_for_teams(team_ids)


# Global singleton instance
corpus_registry = CorpusRegistry()
