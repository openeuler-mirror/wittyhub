"""Rename security_score to risk_score in skills, skill_versions, and agents tables.

Revision ID: 006_rename_security_score_to_risk_score
Revises: 005_add_agent_fields
Create Date: 2026-07-21 00:00:00

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_rename_to_risk_score"
down_revision: Union[str, None] = "005_add_agent_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("skills", "security_score", new_column_name="risk_score")
    op.alter_column("skill_versions", "security_score", new_column_name="risk_score")
    op.alter_column("agents", "security_score", new_column_name="risk_score")
    # agent_versions does not have this column


def downgrade() -> None:
    op.alter_column("skills", "risk_score", new_column_name="security_score")
    op.alter_column("skill_versions", "risk_score", new_column_name="security_score")
    op.alter_column("agents", "risk_score", new_column_name="security_score")
    # agent_versions does not have this column
