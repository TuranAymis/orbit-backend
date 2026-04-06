"""add user roles and moderator tables

Revision ID: c4f8d2e19b7a
Revises: b7e3a9d4c210
Create Date: 2026-04-05 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c4f8d2e19b7a"
down_revision: str | None = "b7e3a9d4c210"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


user_role_enum = postgresql.ENUM("USER", "MODERATOR", "ADMIN", name="user_role_enum")


def upgrade() -> None:
    user_role_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.Enum("USER", "MODERATOR", "ADMIN", name="user_role_enum"),
            nullable=False,
            server_default="USER",
        ),
    )
    op.alter_column("users", "role", server_default=None)

    op.create_table(
        "group_moderators",
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_moderators_group_user"),
    )
    op.create_index("ix_group_moderators_group_id", "group_moderators", ["group_id"], unique=False)
    op.create_index("ix_group_moderators_user_id", "group_moderators", ["user_id"], unique=False)

    op.create_table(
        "event_moderators",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_moderators_event_user"),
    )
    op.create_index("ix_event_moderators_event_id", "event_moderators", ["event_id"], unique=False)
    op.create_index("ix_event_moderators_user_id", "event_moderators", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_event_moderators_user_id", table_name="event_moderators")
    op.drop_index("ix_event_moderators_event_id", table_name="event_moderators")
    op.drop_table("event_moderators")

    op.drop_index("ix_group_moderators_user_id", table_name="group_moderators")
    op.drop_index("ix_group_moderators_group_id", table_name="group_moderators")
    op.drop_table("group_moderators")

    op.drop_column("users", "role")
    user_role_enum.drop(op.get_bind(), checkfirst=True)
