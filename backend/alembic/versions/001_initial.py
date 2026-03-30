"""Initial migration — all tables

Revision ID: 001
Revises:
Create Date: 2026-03-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("invite_code_used", sa.String(50), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("phone_numbers", sa.Text(), nullable=True),
        sa.Column("email_addresses", sa.Text(), nullable=True),
        sa.Column("addresses", sa.Text(), nullable=True),
        sa.Column("age_range", sa.Text(), nullable=True),
        sa.Column("relatives", sa.Text(), nullable=True),
        sa.Column("telegram_chat_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "scan_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_profiles.id"), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("brokers_targeted", postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("brokers_completed", postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("brokers_failed", postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("listings_found", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "found_listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("scan_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scan_jobs.id"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_profiles.id"), nullable=False, index=True),
        sa.Column("broker", sa.String(50), nullable=False),
        sa.Column("listing_url", sa.Text(), nullable=False),
        sa.Column("name_on_listing", sa.String(255), nullable=False),
        sa.Column("phones", postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("emails", postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("addresses", postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("age", sa.String(20), nullable=True),
        sa.Column("relatives", postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("priority", sa.Float(), nullable=False, server_default=sa.text("0.5")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending_review'")),
        sa.Column("removal_method", sa.String(20), nullable=True),
        sa.Column("manual_instructions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "removal_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("found_listings.id"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_profiles.id"), nullable=False, index=True),
        sa.Column("broker", sa.String(50), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recheck_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'removal_sent'")),
    )

    op.create_table(
        "invite_codes",
        sa.Column("code", sa.String(8), primary_key=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("used_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_table("invite_codes")
    op.drop_table("removal_requests")
    op.drop_table("found_listings")
    op.drop_table("scan_jobs")
    op.drop_table("user_profiles")
