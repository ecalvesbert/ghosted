"""Removal-first refactor: drop scan/listing tables, create removal_batches, alter removal_requests

Revision ID: 004
Revises: 003
Create Date: 2026-03-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create removal_batches table
    op.create_table(
        "removal_batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("user_profiles.id"), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("brokers_targeted", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("brokers_completed", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("brokers_failed", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("total_removals", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Alter removal_requests: drop listing_id, add new columns
    # First drop the foreign key constraint on listing_id
    op.drop_constraint("removal_requests_listing_id_fkey", "removal_requests", type_="foreignkey")
    op.drop_column("removal_requests", "listing_id")

    # Add new columns
    op.add_column("removal_requests", sa.Column("batch_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("removal_requests_batch_id_fkey", "removal_requests", "removal_batches", ["batch_id"], ["id"])
    op.create_index("ix_removal_requests_batch_id", "removal_requests", ["batch_id"])

    op.add_column("removal_requests", sa.Column("opt_out_url", sa.Text(), nullable=True))
    op.add_column("removal_requests", sa.Column("live_view_url", sa.Text(), nullable=True))
    op.add_column("removal_requests", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()))

    # Update status default
    op.alter_column("removal_requests", "status", server_default="pending")

    # Make method nullable (was required before)
    op.alter_column("removal_requests", "method", nullable=True)

    # Drop old tables
    op.drop_table("found_listings")
    op.drop_table("scan_jobs")


def downgrade() -> None:
    # Recreate scan_jobs
    op.create_table(
        "scan_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("user_profiles.id"), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("brokers_targeted", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("brokers_completed", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("brokers_failed", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("listings_found", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("live_view_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Recreate found_listings
    op.create_table(
        "found_listings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_job_id", UUID(as_uuid=True), sa.ForeignKey("scan_jobs.id"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("user_profiles.id"), nullable=False, index=True),
        sa.Column("broker", sa.String(50), nullable=False),
        sa.Column("listing_url", sa.Text(), nullable=False),
        sa.Column("name_on_listing", sa.String(255), nullable=False),
        sa.Column("phones", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("emails", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("addresses", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("age", sa.String(20), nullable=True),
        sa.Column("relatives", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("priority", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending_review"),
        sa.Column("removal_method", sa.String(20), nullable=True),
        sa.Column("manual_instructions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Revert removal_requests changes
    op.drop_column("removal_requests", "created_at")
    op.drop_column("removal_requests", "live_view_url")
    op.drop_column("removal_requests", "opt_out_url")
    op.drop_index("ix_removal_requests_batch_id", "removal_requests")
    op.drop_constraint("removal_requests_batch_id_fkey", "removal_requests", type_="foreignkey")
    op.drop_column("removal_requests", "batch_id")

    # Re-add listing_id
    op.add_column("removal_requests", sa.Column("listing_id", UUID(as_uuid=True), nullable=False))
    op.create_foreign_key("removal_requests_listing_id_fkey", "removal_requests", "found_listings", ["listing_id"], ["id"])
    op.create_index("ix_removal_requests_listing_id", "removal_requests", ["listing_id"])

    op.alter_column("removal_requests", "method", nullable=False)
    op.alter_column("removal_requests", "status", server_default="removal_sent")

    # Drop removal_batches
    op.drop_table("removal_batches")
