from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.utils.enums import MembershipLevel, UserRole

if TYPE_CHECKING:
    from app.models.chat import Chat
    from app.models.event_participant import EventParticipant
    from app.models.event_moderator import EventModerator
    from app.models.group import Group
    from app.models.group_moderator import GroupModerator
    from app.models.membership import Membership
    from app.models.notification import Notification
    from app.models.payment import Payment
    from app.models.user_settings import UserSettings


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    membership_level: Mapped[MembershipLevel] = mapped_column(
        Enum(MembershipLevel, name="membership_level_enum"),
        nullable=False,
        default=MembershipLevel.FREE,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum"),
        nullable=False,
        default=UserRole.USER,
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
    event_participants: Mapped[list["EventParticipant"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    moderated_groups: Mapped[list["GroupModerator"]] = relationship(
        foreign_keys="GroupModerator.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    assigned_group_moderators: Mapped[list["GroupModerator"]] = relationship(
        foreign_keys="GroupModerator.assigned_by",
        back_populates="assigned_by_user",
    )
    moderated_events: Mapped[list["EventModerator"]] = relationship(
        foreign_keys="EventModerator.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    assigned_event_moderators: Mapped[list["EventModerator"]] = relationship(
        foreign_keys="EventModerator.assigned_by",
        back_populates="assigned_by_user",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    settings: Mapped[UserSettings | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
