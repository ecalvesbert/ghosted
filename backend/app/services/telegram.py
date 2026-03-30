"""
Telegram Bot API notification service.

Sends notifications via the Telegram Bot API using httpx.
Silently skips if telegram is not configured (no token or no chat_id).
Never logs PII content — only logs delivery status.
"""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


async def send_notification(chat_id: str, message: str) -> None:
    """Send a plain text message to a Telegram chat. Silently skips on misconfiguration."""
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN

    if not chat_id or not token:
        return

    url = TELEGRAM_API_BASE.format(token=token)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={"chat_id": chat_id, "text": message})
            if resp.status_code == 200:
                logger.info("Telegram notification sent to chat (id redacted)")
            else:
                logger.warning(
                    "Telegram API returned %d for chat (id redacted)", resp.status_code
                )
    except Exception:
        logger.exception("Failed to send Telegram notification (chat id redacted)")


async def send_scan_complete(chat_id: str, scan_job) -> None:
    """Notify user that a scan has completed."""
    brokers_completed = scan_job.brokers_completed or []
    listings_found = scan_job.listings_found or 0
    broker_count = len(brokers_completed)
    broker_label = "broker" if broker_count == 1 else "brokers"

    message = (
        f"\U0001f50d Scan complete! Found {listings_found} listing"
        f"{'s' if listings_found != 1 else ''} across {broker_count} {broker_label}. "
        f"Review them now."
    )
    await send_notification(chat_id, message)


async def send_removal_confirmed(chat_id: str, listing) -> None:
    """Notify user that a listing removal has been confirmed."""
    message = (
        f"\u2705 Removal confirmed: {listing.broker} listing "
        f"for {listing.name_on_listing} has been removed."
    )
    await send_notification(chat_id, message)


async def send_removal_failed(chat_id: str, listing, error: str = "") -> None:
    """Notify user that a listing removal has failed."""
    error_part = f" \u2014 {error}" if error else ""
    message = (
        f"\u26a0\ufe0f Removal failed: {listing.broker}{error_part}. "
        f"Manual steps may be needed."
    )
    await send_notification(chat_id, message)
