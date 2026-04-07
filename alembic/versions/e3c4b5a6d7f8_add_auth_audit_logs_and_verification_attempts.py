"""add auth audit logs and verification attempts

Revision ID: e3c4b5a6d7f8
Revises: d9b1f7a4e2c3
Create Date: 2026-04-07 00:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e3c4b5a6d7f8"
down_revision: str | None = "d9b1f7a4e2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "email_verification_codes",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("email_verification_codes", "attempt_count", server_default=None)

    op.create_table(
        "auth_audit_logs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("detail", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_audit_logs_email", "auth_audit_logs", ["email"], unique=False)
    op.create_index(
        "ix_auth_audit_logs_event_type",
        "auth_audit_logs",
        ["event_type"],
        unique=False,
    )
    op.create_index("ix_auth_audit_logs_user_id", "auth_audit_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_auth_audit_logs_user_id", table_name="auth_audit_logs")
    op.drop_index("ix_auth_audit_logs_event_type", table_name="auth_audit_logs")
    op.drop_index("ix_auth_audit_logs_email", table_name="auth_audit_logs")
    op.drop_table("auth_audit_logs")

    op.drop_column("email_verification_codes", "attempt_count")
