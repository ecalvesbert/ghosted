import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, nullable=False)  # [ENCRYPTED]
    hashed_password = Column(String(255), nullable=False)
    invite_code_used = Column(String(50), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # PII — all encrypted at rest
    full_name = Column(Text, nullable=True)           # [ENCRYPTED]
    phone_numbers = Column(Text, nullable=True)       # [ENCRYPTED] JSON list
    email_addresses = Column(Text, nullable=True)     # [ENCRYPTED] JSON list
    addresses = Column(Text, nullable=True)           # [ENCRYPTED] JSON list
    age_range = Column(Text, nullable=True)           # [ENCRYPTED]
    relatives = Column(Text, nullable=True)           # [ENCRYPTED] JSON list
    telegram_chat_id = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
