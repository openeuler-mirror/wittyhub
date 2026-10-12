"""Add an approximate-nearest-neighbor index for skill embeddings."""

from typing import Sequence, Union

from alembic import op

revision: str = "014_add_skill_embedding_hnsw"
down_revision: Union[str, None] = "013_contributors_git_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX idx_skills_embedding_hnsw
        ON skills
        USING hnsw (embedding vector_l2_ops)
        WHERE embedding IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_skills_embedding_hnsw")
