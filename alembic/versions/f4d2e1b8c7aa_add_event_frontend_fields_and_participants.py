"""add event frontend fields and participants

Revision ID: f4d2e1b8c7aa
Revises: 9a4e7c2b1f13
Create Date: 2026-04-03 21:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4d2e1b8c7aa"
down_revision: Union[str, None] = "9a4e7c2b1f13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("cover_image_url", sa.String(length=2048), nullable=True))
    op.create_table(
        "event_participants",
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("event_participants")
    op.drop_column("events", "cover_image_url")
