from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.enums import MembershipLevel

if TYPE_CHECKING:
    from app.models.chat import Chat
    from app.models.group import Group
    from app.models.membership import Membership
    from app.models.payment import Payment


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    membership_level: Mapped[MembershipLevel] = mapped_column(
        Enum(MembershipLevel, name="membership_level_enum"),
        nullable=False,
        default=MembershipLevel.FREE,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    groups_owned: Mapped[list["Group"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sent_messages: Mapped[list["Chat"]] = relationship(
        back_populates="sender",
        cascade="all, delete-orphan",
    )
