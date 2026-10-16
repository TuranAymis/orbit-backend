from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserBadge(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_key", name="uq_user_badges_user_key"),
        Index("ix_user_badges_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    badge_key: Mapped[str] = mapped_column(String(100), nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="badges")
