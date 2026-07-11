"""
SQLAlchemy declarative base and shared mixins.
All models import Base from here to share the same metadata object.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Single metadata instance shared across all models."""
    pass


class TimestampMixin:
    """
    Adds created_at / updated_at to any model.
    server_default delegates to PostgreSQL — accurate even for bulk inserts.
    onupdate keeps updated_at fresh without application-level intervention.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """
    UUID primary key.
    UUIDs are preferred over sequential integers in financial systems:
    - No enumeration attacks
    - Safe for distributed ID generation
    - Globally unique across shards
    """
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
