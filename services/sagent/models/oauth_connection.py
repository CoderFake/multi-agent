"""OAuth connection model.

Stores third-party OAuth tokens (Google Drive, etc.) separate from app auth.
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class OAuthConnection(Base):
    """OAuth connections for external services.

    Stores access/refresh tokens for Google Drive and other integrations.
    Keyed by (user_id, provider) — one connection per provider per user.

    Cache keys (future Redis):
        - oauth:{user_id}:{provider} → token details
        - oauth_list:{user_id} → list of connected providers
    """

    __tablename__ = "oauth_connections"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column("userId", String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)  # 'google_drive'
    access_token: Mapped[str] = mapped_column("accessToken", String, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column("refreshToken", String)
    token_expiry: Mapped[datetime | None] = mapped_column("tokenExpiry", DateTime(timezone=True))
    scopes: Mapped[str | None] = mapped_column(String)  # space-separated
    provider_email: Mapped[str | None] = mapped_column("providerEmail", String)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("oauth_connections_user_id_idx", "userId"),
        UniqueConstraint("userId", "provider", name="oauth_connections_user_provider_uq"),
    )

    def __repr__(self) -> str:
        return f"<OAuthConnection user={self.user_id} provider={self.provider}>"

    # ── Cache helpers (future Redis) ─────────────────────────────────
    @staticmethod
    def cache_key(user_id: str, provider: str) -> str:
        return f"oauth:{user_id}:{provider}"

    @staticmethod
    def cache_key_list(user_id: str) -> str:
        return f"oauth_list:{user_id}"

