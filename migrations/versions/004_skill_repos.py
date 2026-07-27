"""empty migration for chain continuity

Revision ID: 004_skill_repos
Revises: 003_add_agent_fields
Create Date: 2026-06-20 00:00:00

"""
from typing import Sequence, Union

from alembic import op

revision: str = "004_skill_repos"
down_revision: Union[str, None] = "003_add_agent_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
