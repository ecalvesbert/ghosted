from enum import Enum


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ListingStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    SKIPPED = "skipped"
    REMOVAL_SENT = "removal_sent"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class RemovalMethod(str, Enum):
    AUTOMATED = "automated"
    MANUAL = "manual"


class BrokerStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    CAPTCHA = "captcha"
