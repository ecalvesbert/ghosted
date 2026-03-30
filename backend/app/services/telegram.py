"""
Telegram Bot API notification service.

Sends notifications via the Telegram Bot API using httpx.
Silently skips if telegram is not configured (no token or no chat_id).
Never logs PII content -- only logs delivery status.
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


async def send_batch_complete(chat_id: str, batch) -> None:
    """Notify user that a removal batch has completed."""
    completed = len(batch.brokers_completed or [])
    failed = len(batch.brokers_failed or [])
    total = batch.total_removals or 0

    message = (
        f"\u2705 Removal batch complete! "
        f"Submitted {total} opt-out request{'s' if total != 1 else ''} "
        f"across {completed} broker{'s' if completed != 1 else ''}."
    )
    if failed > 0:
        message += f" {failed} broker{'s' if failed != 1 else ''} failed."

    await send_notification(chat_id, message)


async def send_removal_confirmed(chat_id: str, broker: str) -> None:
    """Notify user that a removal has been confirmed."""
    message = f"\u2705 Removal confirmed: your opt-out from {broker} has been verified."
    await send_notification(chat_id, message)


async def send_removal_failed(chat_id: str, broker: str, error: str = "") -> None:
    """Notify user that a removal has failed."""
    error_part = f" \u2014 {error}" if error else ""
    message = (
        f"\u26a0\ufe0f Removal failed: {broker}{error_part}. "
        f"Manual steps may be needed."
    )
    await send_notification(chat_id, message)
