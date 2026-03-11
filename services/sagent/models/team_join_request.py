"""Team join request model.

Self-service team membership with admin approval.
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class TeamJoinRequest(Base):
    """Team join requests with token-based email approval.

    Cache keys (future Redis):
        - join_request:{id} → request details
        - join_request_by_token:{token} → request lookup
        - join_requests:{team_id} → pending requests for team
    """

    __tablename__ = "team_join_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)  # requesting user email
    team_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)  # UUID for email links
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_by: Mapped[str | None] = mapped_column(String)  # admin email
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("team_join_requests_token_idx", "token"),
        Index("team_join_requests_user_id_idx", "user_id"),
        Index("team_join_requests_team_id_idx", "team_id"),
    )

    def __repr__(self) -> str:
        return f"<TeamJoinRequest user={self.user_id} team={self.team_id} status={self.status}>"

