from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class InviteCode(Base):
    __tablename__ = "invite_codes"

    code = Column(String(8), primary_key=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    used_by = Column(UUID(as_uuid=True), nullable=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_used = Column(Boolean, default=False, nullable=False)
