"""add chat room states

Revision ID: f1a2b3c4d5e6
Revises: e3c4b5a6d7f8
Create Date: 2026-04-07 22:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e3c4b5a6d7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


chat_room_type_enum = postgresql.ENUM("group", "event", name="chat_room_type_enum", create_type=False)


def upgrade() -> None:
    chat_room_type_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "chat_room_states",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_type", chat_room_type_enum, nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_read_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_muted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("muted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["last_read_message_id"], ["chats.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "room_type", "room_id", name="uq_chat_room_states_user_room"),
    )
    op.create_index("ix_chat_room_states_room", "chat_room_states", ["room_type", "room_id"], unique=False)
    op.create_index("ix_chat_room_states_user_id", "chat_room_states", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_chat_room_states_user_id", table_name="chat_room_states")
    op.drop_index("ix_chat_room_states_room", table_name="chat_room_states")
    op.drop_table("chat_room_states")
    chat_room_type_enum.drop(op.get_bind(), checkfirst=True)
