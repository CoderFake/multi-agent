"""
SQLAlchemy Base and mixins for all CMS models.
Pattern copied from embed_chatbot/backend/app/models/base.py.
"""
from sqlalchemy import Column, DateTime, event
from sqlalchemy.orm import declarative_base

from app.utils.datetime_utils import now

Base = declarative_base()


class TimestampMixin:
    """
    Mixin for created_at and updated_at timestamp fields.
    Timestamps are automatically set via SQLAlchemy events.
    Uses timezone-aware timestamps (TIMESTAMP WITH TIME ZONE in PostgreSQL).
    """
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


@event.listens_for(TimestampMixin, "before_insert", propagate=True)
def set_created_at(mapper, connection, target):
    """Set created_at and updated_at on insert."""
    current_time = now()
    target.created_at = current_time
    target.updated_at = current_time


@event.listens_for(TimestampMixin, "before_update", propagate=True)
def set_updated_at(mapper, connection, target):
    """Set updated_at on update."""
    target.updated_at = now()


class SoftDeleteMixin:
    """
    Mixin for soft delete support.
    Uses timezone-aware timestamps (TIMESTAMP WITH TIME ZONE in PostgreSQL).
    """
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    def soft_delete(self) -> None:
        """Mark record as deleted."""
        self.deleted_at = now()

    def restore(self) -> None:
        """Restore soft-deleted record."""
        self.deleted_at = None

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None
