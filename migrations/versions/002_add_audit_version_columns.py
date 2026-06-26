"""Add version metadata columns to security audits.

Revision ID: 002_add_audit_version_columns
Revises: 001_initial_schema
Create Date: 2026-06-04 00:05:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_add_audit_version_columns"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("security_audits", sa.Column("version", sa.String(length=50), nullable=True))
    op.add_column("security_audits", sa.Column("commit_id", sa.String(length=40), nullable=True))
    op.create_index(
        "idx_audits_version",
        "security_audits",
        ["resource_id", "version", "commit_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_audits_version", table_name="security_audits")
    op.drop_column("security_audits", "commit_id")
    op.drop_column("security_audits", "version")
