"""Team membership service for RAG access control (read-only).

Provides a unified interface for determining user team membership.
Uses SQLAlchemy ORM models.

Usage:
    from services.rag import team_service

    teams = team_service.get_user_teams("user@example.com")
"""

import logging
from abc import ABC, abstractmethod

from sqlalchemy import func

from config.settings import settings
from core.database import get_session
from models.user_team import UserTeam

logger = logging.getLogger(__name__)


class TeamMembershipService(ABC):
    """Abstract base class for team membership services."""

    @abstractmethod
    def get_user_teams(self, user_id: str) -> list[str]:
        """Get the team IDs a user belongs to."""
        pass

    @abstractmethod
    def is_user_in_team(self, user_id: str, team_id: str) -> bool:
        """Check if a user is a member of a specific team."""
        pass


class DatabaseTeamService(TeamMembershipService):
    """Team membership from user_teams database table via ORM.

    Used when Firebase Auth is the identity provider and team membership
    is managed within the application.
    """

    def get_user_teams(self, user_id: str) -> list[str]:
        """Get teams from user_teams table using ORM."""
        normalised_id = user_id.strip().lower()
        session = get_session()
        try:
            teams = (
                session.query(UserTeam.team_id)
                .filter(func.lower(UserTeam.user_id) == normalised_id)
                .all()
            )
            result = [t.team_id for t in teams]
            logger.debug(f"User {normalised_id} teams: {result}")
            return result
        finally:
            session.close()

    def is_user_in_team(self, user_id: str, team_id: str) -> bool:
        """Check membership in user_teams table using ORM."""
        normalised_id = user_id.strip().lower()
        session = get_session()
        try:
            exists = (
                session.query(UserTeam)
                .filter(
                    func.lower(UserTeam.user_id) == normalised_id,
                    UserTeam.team_id == team_id,
                )
                .first()
            )
            return exists is not None
        finally:
            session.close()


def get_team_service() -> TeamMembershipService:
    """Get the appropriate team membership service based on environment.

    Currently only supports 'database' (default).
    Future: 'google_groups', 'azure_ad'.
    """
    provider = settings.TEAM_MEMBERSHIP_PROVIDER

    if provider == "google_groups":
        raise NotImplementedError("GoogleGroupsTeamService not yet implemented.")
    elif provider == "azure_ad":
        raise NotImplementedError("AzureADTeamService not yet implemented.")
    else:
        return DatabaseTeamService()


# Default service instance
team_service = get_team_service()
