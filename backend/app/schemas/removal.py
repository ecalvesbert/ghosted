from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class RemovalCreateRequest(BaseModel):
    brokers: list[str]


class RemovalRequestResponse(BaseModel):
    id: UUID
    user_id: UUID
    batch_id: Optional[UUID]
    broker: str
    status: str
    method: Optional[str]
    opt_out_url: Optional[str]
    submitted_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    recheck_after: Optional[datetime]
    attempts: int
    last_error: Optional[str]
    notes: Optional[str]
    live_view_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class RemovalBatchResponse(BaseModel):
    id: UUID
    user_id: UUID
    status: str
    brokers_targeted: list[str]
    brokers_completed: list[str]
    brokers_failed: list[str]
    total_removals: int
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RemovalSummaryResponse(BaseModel):
    total: int
    pending: int
    in_progress: int
    submitted: int
    needs_verification: int
    confirmed: int
    failed: int
