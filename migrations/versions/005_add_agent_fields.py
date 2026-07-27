"""empty migration for chain continuity

Revision ID: 005_add_agent_fields
Revises: 004_skill_repos
Create Date: 2026-06-28 00:00:00

"""
from typing import Sequence, Union

from alembic import op

revision: str = "005_add_agent_fields"
down_revision: Union[str, None] = "004_skill_repos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
