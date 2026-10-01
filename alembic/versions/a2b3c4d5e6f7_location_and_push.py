"""Add event coordinates and web push tables."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None

def upgrade():
    for name, kind in (("city", sa.String(255)), ("latitude", sa.Float()), ("longitude", sa.Float())):
        op.add_column("events", sa.Column(name, kind, nullable=True))
        op.add_column("groups", sa.Column(name, kind, nullable=True))
    op.create_index("ix_events_lat_lon", "events", ["latitude", "longitude"])
    op.create_index("ix_groups_lat_lon", "groups", ["latitude", "longitude"])
    op.create_table("notification_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("category", sa.String(100), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("push_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False, unique=True),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.String(512), nullable=True))
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])

def downgrade():
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
    op.drop_table("notification_preferences")
    op.drop_index("ix_events_lat_lon", table_name="events")
    op.drop_index("ix_groups_lat_lon", table_name="groups")
    for name in ("longitude", "latitude", "city"):
        op.drop_column("events", name)
        op.drop_column("groups", name)
