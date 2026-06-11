"""community reports: title/summary/keywords on communities (SP2.3b).

Revision ID: 011_community_reports
Revises: 010_labeled_pairs
Create Date: 2026-06-10
"""

import sqlalchemy as sa
from alembic import op

revision = "011_community_reports"
down_revision = "010_labeled_pairs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("communities", sa.Column("title", sa.String(200), nullable=True))
    op.add_column("communities", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("communities", sa.Column("keywords", sa.Text(), nullable=True))
    op.add_column("communities", sa.Column("report_generated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("communities", "report_generated_at")
    op.drop_column("communities", "keywords")
    op.drop_column("communities", "summary")
    op.drop_column("communities", "title")
