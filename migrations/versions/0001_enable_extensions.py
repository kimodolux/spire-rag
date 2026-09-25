"""enable pgvector and pg_trgm extensions

Revision ID: 0001_enable_extensions
Revises:
Create Date: 2026-09-25 10:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_enable_extensions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS vector")
