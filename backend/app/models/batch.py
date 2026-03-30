import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.database import Base


class RemovalBatch(Base):
    __tablename__ = "removal_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")
    # Status values: pending, running, done, failed
    brokers_targeted = Column(ARRAY(String), nullable=False, default=list)
    brokers_completed = Column(ARRAY(String), nullable=False, default=list)
    brokers_failed = Column(ARRAY(String), nullable=False, default=list)
    total_removals = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
