"""Add notes column to removal_requests

Revision ID: 005
Revises: 004
Create Date: 2026-03-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("removal_requests", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("removal_requests", "notes")
