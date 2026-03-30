"""
Scan engine — orchestrates sequential broker scanning for a user.

Decrypts the user's profile ONCE, iterates brokers sequentially,
persists results to PostgreSQL after each broker completes.
DecryptedProfile is ephemeral and never persisted.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.brokers import BROKER_REGISTRY
from app.brokers.base import BrokerError
from app.database import SessionLocal
from app.models.listing import FoundListing
from app.models.scan import ScanJob
from app.models.user import UserProfile
from app.services.encryption import decrypt_profile

logger = logging.getLogger(__name__)

DEFAULT_BROKER_ORDER = ["spokeo", "whitepages", "beenverified", "intelius", "peoplefinder"]


def run_scan_sync(scan_id: str, user_id: str, broker_slugs: list[str] | None = None) -> str:
    """
    Synchronous entry point — runs the scan for a specific ScanJob.
    Returns the scan_job id as a string.
    Called from the Celery task.
    """
    db = SessionLocal()
    try:
        # Find or validate user
        user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Resolve broker list
        slugs = broker_slugs or DEFAULT_BROKER_ORDER
        # Only include brokers that exist in registry
        slugs = [s for s in slugs if s in BROKER_REGISTRY]

        # Find the specific scan job by ID
        scan = db.query(ScanJob).filter(ScanJob.id == scan_id, ScanJob.user_id == user_id).first()
        if not scan:
            raise ValueError(f"Scan job {scan_id} not found for user {user_id}")

        scan.status = "running"
        scan.started_at = datetime.now(timezone.utc)
        db.commit()

        # Decrypt profile ONCE — ephemeral, in-memory only
        decrypted = decrypt_profile(user)

        try:
            for slug in slugs:
                adapter = BROKER_REGISTRY.get(slug)
                if not adapter:
                    scan.brokers_failed = list(scan.brokers_failed or []) + [slug]
                    db.commit()
                    continue

                try:
                    # Callback to store live view URL on the scan job
                    def on_session_created(live_url: str):
                        scan.live_view_url = live_url
                        db.commit()

                    # Run adapter with per-broker timeout
                    listings = asyncio.run(
                        asyncio.wait_for(
                            adapter.search(decrypted, on_session_created=on_session_created),
                            timeout=adapter.timeout_seconds,
                        )
                    )

                    # Persist listings
                    for listing in listings:
                        db_listing = FoundListing(
                            id=listing.id,
                            scan_job_id=scan.id,
                            user_id=user.id,
                            broker=listing.broker,
                            listing_url=listing.listing_url,
                            name_on_listing=listing.name_on_listing,
                            phones=listing.phones,
                            emails=listing.emails,
                            addresses=listing.addresses,
                            age=listing.age,
                            relatives=listing.relatives,
                            priority=listing.priority,
                            status=listing.status,
                            removal_method=listing.removal_method,
                            manual_instructions=listing.manual_instructions,
                        )
                        db.add(db_listing)

                    scan.brokers_completed = list(scan.brokers_completed or []) + [slug]
                    scan.listings_found = (scan.listings_found or 0) + len(listings)
                    db.commit()

                except asyncio.TimeoutError:
                    logger.warning("Broker %s timed out after %ds", slug, adapter.timeout_seconds)
                    scan.brokers_failed = list(scan.brokers_failed or []) + [slug]
                    db.commit()

                except BrokerError as exc:
                    logger.warning("Broker %s failed: %s", slug, exc.message)
                    scan.brokers_failed = list(scan.brokers_failed or []) + [slug]
                    db.commit()

                except Exception:
                    logger.exception("Unexpected error scanning broker %s", slug)
                    scan.brokers_failed = list(scan.brokers_failed or []) + [slug]
                    db.commit()

            # All brokers processed
            scan.status = "done"
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()

            # Send Telegram notification if configured
            if user.telegram_chat_id:
                try:
                    from app.services.telegram import send_scan_complete
                    asyncio.run(send_scan_complete(user.telegram_chat_id, scan))
                except Exception:
                    logger.exception("Failed to send scan-complete Telegram notification")

        except Exception as exc:
            logger.exception("Scan failed fatally")
            scan.status = "failed"
            scan.error = str(exc)[:1000]
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()

        # DecryptedProfile goes out of scope here — never persisted
        return str(scan.id)

    finally:
        db.close()
