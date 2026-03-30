import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.database import Base


class FoundListing(Base):
    __tablename__ = "found_listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_job_id = Column(UUID(as_uuid=True), ForeignKey("scan_jobs.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), nullable=False, index=True)
    broker = Column(String(50), nullable=False)
    listing_url = Column(Text, nullable=False)
    name_on_listing = Column(String(255), nullable=False)
    phones = Column(ARRAY(String), nullable=False, default=list)
    emails = Column(ARRAY(String), nullable=False, default=list)
    addresses = Column(ARRAY(String), nullable=False, default=list)
    age = Column(String(20), nullable=True)
    relatives = Column(ARRAY(String), nullable=False, default=list)
    priority = Column(Float, nullable=False, default=0.5)
    status = Column(String(20), nullable=False, default="pending_review")  # ListingStatus
    removal_method = Column(String(20), nullable=True)  # RemovalMethod
    manual_instructions = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
