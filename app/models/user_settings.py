from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserSettings(TimestampMixin, Base):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    email_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    push_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    marketing_emails: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    profile_visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="public")
    theme_preference: Mapped[str] = mapped_column(String(20), nullable=False, default="dark")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")

    user: Mapped["User"] = relationship(back_populates="settings")
