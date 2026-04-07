from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.enums import ChatRoomType

if TYPE_CHECKING:
    from app.models.chat import Chat
    from app.models.user import User


class ChatRoomState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_room_states"
    __table_args__ = (
        UniqueConstraint("user_id", "room_type", "room_id", name="uq_chat_room_states_user_room"),
        Index("ix_chat_room_states_user_id", "user_id"),
        Index("ix_chat_room_states_room", "room_type", "room_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    room_type: Mapped[ChatRoomType] = mapped_column(
        Enum(
            ChatRoomType,
            name="chat_room_type_enum",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_read_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_muted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    muted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="chat_room_states")
    last_read_message: Mapped["Chat | None"] = relationship()
