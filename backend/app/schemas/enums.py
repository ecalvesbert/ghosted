from enum import Enum


class RemovalStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    NEEDS_VERIFICATION = "needs_verification"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class BatchStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class RemovalMethod(str, Enum):
    AUTOMATED = "automated"
    MANUAL = "manual"


class BrokerStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    CAPTCHA = "captcha"
