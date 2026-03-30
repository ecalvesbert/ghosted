import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class RemovalRequest(Base):
    __tablename__ = "removal_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("found_listings.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, index=True)
    broker = Column(String(50), nullable=False)
    method = Column(String(20), nullable=False)  # RemovalMethod
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    recheck_after = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="removal_sent")  # ListingStatus
