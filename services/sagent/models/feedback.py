"""Feedback model.

User feedback submissions with categories.
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Feedback(Base):
    """User feedback submissions.

    Cache keys (future Redis):
        - feedback:{id} → feedback details
        - feedback_list:{user_id} → user's feedback history
    """

    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)  # bug|feature_request|question|other
    message: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("feedback_user_id_idx", "user_id"),
        Index("feedback_created_at_idx", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Feedback id={self.id} category={self.category}>"

