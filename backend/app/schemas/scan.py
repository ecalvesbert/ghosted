from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ScanCreateRequest(BaseModel):
    brokers: Optional[list[str]] = None


class ScanJobResponse(BaseModel):
    id: UUID
    user_id: UUID
    status: str
    brokers_targeted: list[str]
    brokers_completed: list[str]
    brokers_failed: list[str]
    listings_found: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]
    live_view_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
