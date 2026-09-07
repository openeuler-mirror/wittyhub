"""Add behavior_events table for front-end tracking.

Revision ID: 013_add_behavior_events
Revises: 012_add_skill_tree_hash
Create Date: 2026-09-04 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013_add_behavior_events"
down_revision: Union[str, None] = "012_add_skill_tree_hash"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "behavior_events",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column("module", sa.String(length=64), nullable=True),
        sa.Column("path", sa.Text(), nullable=True),
        sa.Column("referrer", sa.Text(), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("skill_id", sa.String(length=255), nullable=True),
        sa.Column("keyword", sa.String(length=255), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("props", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index("idx_events_date", "behavior_events", [sa.text("created_at DESC")])
    op.create_index("idx_events_event", "behavior_events", ["event"])
    op.create_index("idx_events_module", "behavior_events", ["module"])
    op.create_index("idx_events_skill", "behavior_events", ["skill_id"])


def downgrade() -> None:
    op.drop_index("idx_events_skill", table_name="behavior_events")
    op.drop_index("idx_events_module", table_name="behavior_events")
    op.drop_index("idx_events_event", table_name="behavior_events")
    op.drop_index("idx_events_date", table_name="behavior_events")
    op.drop_table("behavior_events")
