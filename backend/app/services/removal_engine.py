"""
Removal engine -- orchestrates sequential broker opt-out submissions for a user.

Decrypts the user's profile ONCE, iterates brokers sequentially,
persists results to PostgreSQL after each broker completes.
DecryptedProfile is ephemeral and never persisted.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from app.brokers import BROKER_REGISTRY
from app.brokers.base import BrokerError
from app.database import SessionLocal
from app.models.batch import RemovalBatch
from app.models.removal import RemovalRequest
from app.models.user import UserProfile
from app.services.encryption import decrypt_profile

logger = logging.getLogger(__name__)


def run_removal_batch_sync(batch_id: str, user_id: str, broker_slugs: list[str]) -> str:
    """
    Synchronous entry point -- runs opt-out submissions for a RemovalBatch.
    Called from BackgroundTasks.
    Returns the batch_id as a string.
    """
    db = SessionLocal()
    try:
        user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        batch = db.query(RemovalBatch).filter(
            RemovalBatch.id == batch_id, RemovalBatch.user_id == user_id
        ).first()
        if not batch:
            raise ValueError(f"Batch {batch_id} not found for user {user_id}")

        batch.status = "running"
        db.commit()

        # Decrypt profile ONCE -- ephemeral, in-memory only
        decrypted = decrypt_profile(user)

        # Only include brokers that exist in the registry
        slugs = [s for s in broker_slugs if s in BROKER_REGISTRY]

        try:
            for slug in slugs:
                adapter = BROKER_REGISTRY.get(slug)
                if not adapter:
                    batch.brokers_failed = list(batch.brokers_failed or []) + [slug]
                    db.commit()
                    continue

                # Create the RemovalRequest for this broker
                removal = RemovalRequest(
                    user_id=user.id,
                    batch_id=batch.id,
                    broker=slug,
                    status="in_progress",
                    opt_out_url=adapter.opt_out_url,
                )
                db.add(removal)
                db.commit()
                db.refresh(removal)

                try:
                    # Callback to store live view URL on the removal request
                    def on_session_created(live_url: str, _removal=removal):
                        _removal.live_view_url = live_url
                        db.commit()

                    # Run adapter with per-broker timeout
                    result = asyncio.run(
                        asyncio.wait_for(
                            adapter.submit_opt_out(decrypted, on_session_created=on_session_created),
                            timeout=adapter.timeout_seconds,
                        )
                    )

                    # Update removal request from adapter result
                    removal.status = result.get("status", "failed")
                    removal.method = result.get("method", "automated")
                    removal.opt_out_url = result.get("opt_out_url", adapter.opt_out_url)
                    removal.notes = result.get("notes")
                    removal.last_error = result.get("notes") if removal.status == "failed" else None
                    removal.attempts = 1
                    removal.submitted_at = datetime.now(timezone.utc)

                    if removal.status in ("submitted", "needs_verification"):
                        removal.recheck_after = datetime.now(timezone.utc) + timedelta(days=3)

                    batch.brokers_completed = list(batch.brokers_completed or []) + [slug]
                    batch.total_removals = (batch.total_removals or 0) + 1
                    db.commit()

                except asyncio.TimeoutError:
                    logger.warning("Broker %s timed out after %ds", slug, adapter.timeout_seconds)
                    removal.status = "failed"
                    removal.method = "manual"
                    removal.last_error = f"Timed out after {adapter.timeout_seconds}s"
                    removal.attempts = 1
                    batch.brokers_failed = list(batch.brokers_failed or []) + [slug]
                    db.commit()

                except BrokerError as exc:
                    logger.warning("Broker %s failed: %s", slug, exc.message)
                    removal.status = "failed"
                    removal.method = "manual"
                    removal.last_error = exc.message
                    removal.attempts = 1
                    batch.brokers_failed = list(batch.brokers_failed or []) + [slug]
                    db.commit()

                except Exception:
                    logger.exception("Unexpected error with broker %s", slug)
                    removal.status = "failed"
                    removal.method = "manual"
                    removal.last_error = "Unexpected error during opt-out submission"
                    removal.attempts = 1
                    batch.brokers_failed = list(batch.brokers_failed or []) + [slug]
                    db.commit()

            # All brokers processed
            batch.status = "done"
            batch.completed_at = datetime.now(timezone.utc)
            db.commit()

            # Send Telegram notification if configured
            if user.telegram_chat_id:
                try:
                    from app.services.telegram import send_batch_complete
                    asyncio.run(send_batch_complete(user.telegram_chat_id, batch))
                except Exception:
                    logger.exception("Failed to send batch-complete Telegram notification")

        except Exception as exc:
            logger.exception("Removal batch failed fatally")
            batch.status = "failed"
            batch.completed_at = datetime.now(timezone.utc)
            db.commit()

        # DecryptedProfile goes out of scope here -- never persisted
        return str(batch.id)

    finally:
        db.close()
