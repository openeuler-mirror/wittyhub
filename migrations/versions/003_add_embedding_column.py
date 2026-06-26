"""Add pgvector embeddings for semantic search.

Revision ID: 003_add_embedding_column
Revises: 002_add_audit_version_columns
Create Date: 2026-06-04 00:10:00

"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_add_embedding_column"
down_revision: Union[str, None] = "002_add_audit_version_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector 索引不依赖 ORM autogenerate，统一由 migration 手写维护
    op.add_column("skills", sa.Column("embedding", Vector(dim=768), nullable=True))
    op.execute('CREATE INDEX idx_skills_embedding ON skills USING ivfflat (embedding vector_l2_ops);')


def downgrade() -> None:
    op.drop_index("idx_skills_embedding", table_name="skills")
    op.drop_column("skills", "embedding")
