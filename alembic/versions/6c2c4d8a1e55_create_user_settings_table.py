"""create user settings table

Revision ID: 6c2c4d8a1e55
Revises: 1b7a5f6f9c2d
Create Date: 2026-04-03 20:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6c2c4d8a1e55"
down_revision: Union[str, None] = "1b7a5f6f9c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("email_notifications", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("push_notifications", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("marketing_emails", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("profile_visibility", sa.String(length=20), nullable=False, server_default="public"),
        sa.Column("theme_preference", sa.String(length=20), nullable=False, server_default="dark"),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
