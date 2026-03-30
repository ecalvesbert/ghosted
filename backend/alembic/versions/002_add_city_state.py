"""Add city and state columns to user_profiles

Revision ID: 002
Revises: 001
Create Date: 2026-03-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("city", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("state", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_profiles", "state")
    op.drop_column("user_profiles", "city")
