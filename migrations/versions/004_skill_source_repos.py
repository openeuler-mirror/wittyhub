"""Add skill source repositories table and skill foreign key.

Revision ID: 004_skill_source_repos
Revises: 003_add_embedding_column
Create Date: 2026-06-06 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "004_skill_source_repos"
down_revision: Union[str, None] = "003_add_embedding_column"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "skill_source_repositories",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("repo_name", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("branch", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("skill_discover_status", sa.String(length=50), nullable=False, server_default=sa.text("'init'")),
        sa.Column("skill_num", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("repo_name", name="uq_skill_source_repositories_repo_name"),
    )

    op.create_index(
        "idx_skill_source_repositories_source",
        "skill_source_repositories",
        ["source"],
    )
    op.create_index(
        "idx_skill_source_repositories_status",
        "skill_source_repositories",
        ["skill_discover_status"],
    )
    op.create_index(
        "idx_skill_source_repositories_created_at",
        "skill_source_repositories",
        [sa.text("created_at DESC")],
    )

    op.add_column(
        "skills",
        sa.Column("skill_source_repository_id", UUID, nullable=False),
    )
    op.create_foreign_key(
        "fk_skills_skill_source_repository_id",
        "skills",
        "skill_source_repositories",
        ["skill_source_repository_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "idx_skills_source_repository_id",
        "skills",
        ["skill_source_repository_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_skills_source_repository_id", table_name="skills")
    op.drop_constraint("fk_skills_skill_source_repository_id", "skills", type_="foreignkey")
    op.drop_column("skills", "skill_source_repository_id")

    op.drop_index(
        "idx_skill_source_repositories_created_at",
        table_name="skill_source_repositories",
    )
    op.drop_index(
        "idx_skill_source_repositories_status",
        table_name="skill_source_repositories",
    )
    op.drop_index(
        "idx_skill_source_repositories_source",
        table_name="skill_source_repositories",
    )
    op.drop_table("skill_source_repositories")
