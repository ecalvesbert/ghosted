import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.database import Base


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")  # ScanStatus enum
    brokers_targeted = Column(ARRAY(String), nullable=False, default=list)
    brokers_completed = Column(ARRAY(String), nullable=False, default=list)
    brokers_failed = Column(ARRAY(String), nullable=False, default=list)
    listings_found = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    live_view_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
