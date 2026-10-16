"""Add earned user badges."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b5c6d7e8f901"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("badge_key", sa.String(100), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "badge_key", name="uq_user_badges_user_key"),
    )
    op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_badges_user_id", table_name="user_badges")
    op.drop_table("user_badges")
