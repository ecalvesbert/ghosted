"""
Status tracking service for removal requests.
Provides summary counts and stale removal detection.
"""

from datetime import datetime, timedelta, timezone
from typing import TypedDict
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.removal import RemovalRequest


class RemovalSummary(TypedDict):
    total: int
    pending: int
    confirmed: int
    failed: int


def get_removal_summary(db: Session, user_id: UUID) -> RemovalSummary:
    """Return counts of removals by status for a user."""
    removals = db.query(RemovalRequest).filter(
        RemovalRequest.user_id == user_id
    ).all()

    summary: RemovalSummary = {"total": 0, "pending": 0, "confirmed": 0, "failed": 0}
    for r in removals:
        summary["total"] += 1
        if r.status == "removal_sent":
            summary["pending"] += 1
        elif r.status == "confirmed":
            summary["confirmed"] += 1
        elif r.status == "failed":
            summary["failed"] += 1

    return summary


def get_stale_removals(db: Session, user_id: UUID, days: int = 7) -> list[RemovalRequest]:
    """Return removal requests still in 'removal_sent' status older than `days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return db.query(RemovalRequest).filter(
        RemovalRequest.user_id == user_id,
        RemovalRequest.status == "removal_sent",
        RemovalRequest.submitted_at < cutoff,
    ).order_by(RemovalRequest.submitted_at.asc()).all()
