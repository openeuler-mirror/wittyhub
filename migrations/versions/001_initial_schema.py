"""Create the initial WittyHub schema.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-06-04 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
ARRAY_TEXT = postgresql.ARRAY(sa.String())


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "unaccent";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')

    op.execute(
        """
        DO $$ BEGIN
            CREATE TEXT SEARCH CONFIGURATION zhcfg (COPY = pg_catalog.simple);
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
        """
    )
    op.execute(
        """
        ALTER TEXT SEARCH CONFIGURATION zhcfg
        ALTER MAPPING FOR asciiword, word WITH unaccent, simple;
        """
    )

    op.create_table(
        "skills",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("skill_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("commit_id", sa.String(length=40), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("tags", ARRAY_TEXT, nullable=True),
        sa.Column("platform", sa.String(length=100), nullable=True),
        sa.Column("extra_metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("security_score", sa.Integer(), nullable=True),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("rating", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "agents",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("agent_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("tags", ARRAY_TEXT, nullable=True),
        sa.Column("extra_metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("security_score", sa.Integer(), nullable=True),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("rating", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("agent_id", name="agents_agent_id_key"),
    )

    op.create_table(
        "security_audits",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("resource_type", sa.String(length=20), nullable=False),
        sa.Column("resource_id", UUID, nullable=False),
        sa.Column("audit_type", sa.String(length=50), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("risk_signals", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("audited_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["resource_id"], ["skills.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "download_history",
        sa.Column("id", UUID, primary_key=True, nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("resource_type", sa.String(length=20), nullable=False),
        sa.Column("resource_id", UUID, nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index("idx_skills_category", "skills", ["category"])
    op.create_index("idx_skills_platform", "skills", ["platform"])
    op.create_index("idx_skills_source", "skills", ["source"])
    op.create_index("idx_skills_created_at", "skills", [sa.text("created_at DESC")])
    op.create_index("idx_skills_tags", "skills", ["tags"], postgresql_using="gin")
    op.create_index(
        "idx_skills_unique",
        "skills",
        ["source", "source_url", "version", "commit_id"],
        unique=True,
    )

    op.create_index("idx_agents_category", "agents", ["category"])
    op.create_index("idx_agents_tags", "agents", ["tags"], postgresql_using="gin")

    op.create_index("idx_audits_resource", "security_audits", ["resource_type", "resource_id"])
    op.create_index("idx_audits_risk_level", "security_audits", ["risk_level"])
    op.create_index("idx_audits_audited_at", "security_audits", [sa.text("audited_at DESC")])

    op.create_index("idx_downloads_resource", "download_history", ["resource_type", "resource_id"])
    op.create_index("idx_downloads_date", "download_history", [sa.text("downloaded_at DESC")])


def downgrade() -> None:
    op.drop_index("idx_downloads_date", table_name="download_history")
    op.drop_index("idx_downloads_resource", table_name="download_history")
    op.drop_index("idx_audits_audited_at", table_name="security_audits")
    op.drop_index("idx_audits_risk_level", table_name="security_audits")
    op.drop_index("idx_audits_resource", table_name="security_audits")
    op.drop_index("idx_agents_tags", table_name="agents")
    op.drop_index("idx_agents_category", table_name="agents")
    op.drop_index("idx_skills_unique", table_name="skills")
    op.drop_index("idx_skills_tags", table_name="skills")
    op.drop_index("idx_skills_created_at", table_name="skills")
    op.drop_index("idx_skills_source", table_name="skills")
    op.drop_index("idx_skills_platform", table_name="skills")
    op.drop_index("idx_skills_category", table_name="skills")

    op.drop_table("download_history")
    op.drop_table("security_audits")
    op.drop_table("agents")
    op.drop_table("skills")
