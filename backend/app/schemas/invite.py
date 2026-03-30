from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class InviteCreateRequest(BaseModel):
    expires_in_days: Optional[int] = None


class InviteCodeResponse(BaseModel):
    code: str
    created_by: UUID
    used_by: Optional[UUID]
    used_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_used: bool

    model_config = {"from_attributes": True}
