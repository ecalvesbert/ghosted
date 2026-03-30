from abc import ABC, abstractmethod
from typing import Optional, Literal

from app.services.encryption import DecryptedProfile
from app.models.listing import FoundListing
from app.models.removal import RemovalRequest


class BrokerError(Exception):
    def __init__(
        self,
        broker: str,
        reason: Literal["captcha", "blocked", "not_found", "timeout", "unknown"],
        message: str,
        fallback_instructions: Optional[str] = None,
    ):
        self.broker = broker
        self.reason = reason
        self.message = message
        self.fallback_instructions = fallback_instructions
        super().__init__(message)


class BrokerAdapter(ABC):
    slug: str
    display_name: str
    opt_out_url: str
    timeout_seconds: int = 120
    rate_limit_rps: float = 0.5
    requires_email_verify: bool = False

    @abstractmethod
    async def search(self, profile: DecryptedProfile) -> list[FoundListing]:
        ...

    @abstractmethod
    async def submit_removal(self, listing: FoundListing) -> RemovalRequest:
        ...

    @abstractmethod
    async def verify_removal(self, request: RemovalRequest) -> RemovalRequest:
        ...
