"""Add local-account password rotation state."""
from alembic import op


revision = "20260715_0002"
down_revision = "20260715_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE")


def downgrade() -> None:
    raise RuntimeError("Destructive password-rotation downgrade is not supported")
