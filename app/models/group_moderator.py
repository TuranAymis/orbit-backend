from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.group import Group
    from app.models.user import User


class GroupModerator(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "group_moderators"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_moderators_group_user"),
        Index("ix_group_moderators_group_id", "group_id"),
        Index("ix_group_moderators_user_id", "user_id"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
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

    group: Mapped["Group"] = relationship(back_populates="moderators")
    user: Mapped["User"] = relationship(
        foreign_keys=[user_id],
        back_populates="moderated_groups",
    )
    assigned_by_user: Mapped["User"] = relationship(
        foreign_keys=[assigned_by],
        back_populates="assigned_group_moderators",
    )
