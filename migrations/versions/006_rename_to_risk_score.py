"""empty migration for chain continuity

Revision ID: 006_rename_to_risk_score
Revises: 005_add_agent_fields
Create Date: 2026-07-05 00:00:00

"""
from typing import Sequence, Union

from alembic import op

revision: str = "006_rename_to_risk_score"
down_revision: Union[str, None] = "005_add_agent_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
