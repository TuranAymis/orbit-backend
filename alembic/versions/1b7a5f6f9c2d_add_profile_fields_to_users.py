"""add profile fields to users

Revision ID: 1b7a5f6f9c2d
Revises: 3e98e3bb388b
Create Date: 2026-04-03 20:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1b7a5f6f9c2d"
down_revision: Union[str, None] = "3e98e3bb388b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("location", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "location")
    op.drop_column("users", "bio")
