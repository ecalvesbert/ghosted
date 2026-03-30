from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class FoundListingResponse(BaseModel):
    id: UUID
    scan_job_id: UUID
    user_id: UUID
    broker: str
    listing_url: str
    name_on_listing: str
    phones: list[str]
    emails: list[str]
    addresses: list[str]
    age: Optional[str]
    relatives: list[str]
    priority: float
    status: str
    removal_method: Optional[str]
    manual_instructions: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ListingUpdateRequest(BaseModel):
    status: Literal["approved", "skipped"]
