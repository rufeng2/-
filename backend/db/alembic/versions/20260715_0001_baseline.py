"""Baseline the current enterprise knowledge schema.

Existing installations must verify their schema and use `alembic stamp
20260715_0001`. Empty databases use `alembic upgrade head`.
"""
from alembic import op

from backend.db.models import Base


revision = "20260715_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    raise RuntimeError("Destructive baseline downgrade is not supported")
