from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class RemovalRequestResponse(BaseModel):
    id: UUID
    listing_id: UUID
    user_id: UUID
    broker: str
    method: str
    submitted_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    recheck_after: Optional[datetime]
    attempts: int
    last_error: Optional[str]
    status: str

    model_config = {"from_attributes": True}


class RemovalSummaryResponse(BaseModel):
    total: int
    pending: int
    confirmed: int
    failed: int
