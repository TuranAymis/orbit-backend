from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.group import Group
    from app.models.user import User


class Chat(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "chats"
    __table_args__ = (
        Index("ix_chats_sender_id", "sender_id"),
        Index("ix_chats_group_id", "group_id"),
        Index("ix_chats_event_id", "event_id"),
        Index("ix_chats_created_at", "created_at"),
    )

    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=True,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    sender: Mapped["User"] = relationship(back_populates="sent_messages")
    group: Mapped[Group | None] = relationship(back_populates="chats")
    event: Mapped[Event | None] = relationship(back_populates="chats")
