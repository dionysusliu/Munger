"""Initial schema bootstrap.

Revision ID: 001_initial
Revises:
Create Date: 2026-06-08
"""

from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.core.database import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    from app.core.database import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind)
