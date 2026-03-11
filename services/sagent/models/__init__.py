"""SQLAlchemy ORM models.

Sagent reads and writes these tables but does NOT create or migrate them.
Schema is owned by Drizzle (web/src/lib/schema.ts).

Usage:
    from models import UserTeam, TeamCorpus, Feedback
    from core.database import get_session
"""

from core.database import Base, get_session
from models.adk_session import AdkSession
from models.feedback import Feedback
from models.oauth_connection import OAuthConnection
from models.team_corpus import TeamCorpus
from models.team_join_request import TeamJoinRequest
from models.user_team import UserTeam

__all__ = [
    "AdkSession",
    "Base",
    "Feedback",
    "OAuthConnection",
    "TeamCorpus",
    "TeamJoinRequest",
    "UserTeam",
    "get_session",
]

