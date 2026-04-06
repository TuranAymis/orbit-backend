from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.user import User


class EventModerator(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "event_moderators"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_moderators_event_user"),
        Index("ix_event_moderators_event_id", "event_id"),
        Index("ix_event_moderators_user_id", "user_id"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    event: Mapped["Event"] = relationship(back_populates="moderators")
    user: Mapped["User"] = relationship(
        foreign_keys=[user_id],
        back_populates="moderated_events",
    )
    assigned_by_user: Mapped["User"] = relationship(
        foreign_keys=[assigned_by],
        back_populates="assigned_event_moderators",
    )
