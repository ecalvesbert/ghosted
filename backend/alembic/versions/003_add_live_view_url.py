"""Add live_view_url column to scan_jobs

Revision ID: 003
Revises: 002
Create Date: 2026-03-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scan_jobs", sa.Column("live_view_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("scan_jobs", "live_view_url")
