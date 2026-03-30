from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class UserProfilePublic(BaseModel):
    id: UUID
    email: str
    full_name: str
    phone_numbers: list[str]
    email_addresses: list[str]
    addresses: list[str]
    age_range: Optional[str]
    relatives: list[str]
    telegram_chat_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserPublic(BaseModel):
    """Minimal user info returned on register/me."""
    id: UUID
    email: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_numbers: Optional[list[str]] = None
    email_addresses: Optional[list[str]] = None
    addresses: Optional[list[str]] = None
    age_range: Optional[str] = None
    relatives: Optional[list[str]] = None
    telegram_chat_id: Optional[str] = None
