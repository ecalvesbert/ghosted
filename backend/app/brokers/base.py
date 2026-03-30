from abc import ABC, abstractmethod
from typing import Callable, Optional, Literal

from app.services.encryption import DecryptedProfile


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
    async def submit_opt_out(
        self,
        profile: DecryptedProfile,
        on_session_created: Callable[[str], None] | None = None,
    ) -> dict:
        """
        Navigate to opt-out page, fill form, submit.
        Returns dict with keys: status, method, notes, opt_out_url (optional).
        """
        ...
