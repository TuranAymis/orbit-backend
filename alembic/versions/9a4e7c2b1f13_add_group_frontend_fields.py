"""add group frontend fields

Revision ID: 9a4e7c2b1f13
Revises: 6c2c4d8a1e55
Create Date: 2026-04-03 20:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a4e7c2b1f13"
down_revision: Union[str, None] = "6c2c4d8a1e55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("groups", sa.Column("cover_image_url", sa.String(length=2048), nullable=True))
    op.add_column("groups", sa.Column("category", sa.String(length=255), nullable=True))
    op.add_column("groups", sa.Column("location", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("groups", "location")
    op.drop_column("groups", "category")
    op.drop_column("groups", "cover_image_url")
