"""User-Team membership model.

Maps users (by email/Firebase UID) to teams for RAG access control.
"""

from sqlalchemy import Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class UserTeam(Base):
    """User team membership.

    Composite primary key (user_id, team_id).
    Used for RAG access control - determines which corpora a user can query.

    Cache keys (future Redis):
        - user_teams:{user_id} → list of team_ids
        - team_members:{team_id} → list of user_ids
    """

    __tablename__ = "user_teams"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    team_id: Mapped[str] = mapped_column(String, primary_key=True)
    role: Mapped[str | None] = mapped_column(String, default="member")
    created_at: Mapped[str] = mapped_column(
        server_default=func.now(),
    )

    __table_args__ = (
        Index("user_teams_user_id_idx", "user_id"),
        Index("user_teams_team_id_idx", "team_id"),
    )

    def __repr__(self) -> str:
        return f"<UserTeam user={self.user_id} team={self.team_id} role={self.role}>"

    # ── Cache helpers (future Redis) ─────────────────────────────────
    @staticmethod
    def cache_key_user_teams(user_id: str) -> str:
        return f"user_teams:{user_id.lower()}"

    @staticmethod
    def cache_key_team_members(team_id: str) -> str:
        return f"team_members:{team_id}"

