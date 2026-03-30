import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class RemovalRequest(Base):
    __tablename__ = "removal_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("removal_batches.id"), nullable=True, index=True)
    broker = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="pending")
    # Status values: pending, in_progress, submitted, needs_verification, confirmed, failed
    method = Column(String(20), nullable=True)  # automated, manual
    opt_out_url = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    recheck_after = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    live_view_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
