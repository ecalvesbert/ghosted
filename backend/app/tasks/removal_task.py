"""
Celery tasks for removal submission and verification.
Results are persisted to PostgreSQL.
"""

import asyncio
import logging
from datetime import datetime, timezone

from app.brokers import BROKER_REGISTRY
from app.brokers.base import BrokerError
from app.database import SessionLocal
from app.models.listing import FoundListing
from app.models.removal import RemovalRequest
from app.models.user import UserProfile
from app.services.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="ghosted.submit_removal", bind=True, max_retries=0)
def submit_removal_task(self, listing_id: str) -> str:
    """
    Submit an opt-out removal for a listing via the broker adapter.
    Returns the removal_request id.
    """
    logger.info("Starting removal submission for listing %s", listing_id)
    db = SessionLocal()
    try:
        listing = db.query(FoundListing).filter(FoundListing.id == listing_id).first()
        if not listing:
            logger.error("Listing %s not found", listing_id)
            raise ValueError(f"Listing {listing_id} not found")

        adapter = BROKER_REGISTRY.get(listing.broker)
        if not adapter:
            logger.error("No adapter for broker %s", listing.broker)
            # Update the existing removal request if one exists
            removal = db.query(RemovalRequest).filter(
                RemovalRequest.listing_id == listing.id,
                RemovalRequest.status == "removal_sent",
            ).first()
            if removal:
                removal.status = "failed"
                removal.last_error = f"No adapter registered for broker: {listing.broker}"
                removal.attempts = (removal.attempts or 0) + 1
            listing.status = "failed"
            listing.updated_at = datetime.now(timezone.utc)
            db.commit()
            _send_telegram_removal_failed(db, listing.user_id, listing, f"No adapter for broker: {listing.broker}")
            raise ValueError(f"No adapter for broker: {listing.broker}")

        # Run the async adapter method
        try:
            result = asyncio.get_event_loop().run_until_complete(
                adapter.submit_removal(listing)
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(adapter.submit_removal(listing))
            finally:
                loop.close()

        # Find the removal request created by the API endpoint
        removal = db.query(RemovalRequest).filter(
            RemovalRequest.listing_id == listing.id,
            RemovalRequest.status == "removal_sent",
        ).order_by(RemovalRequest.submitted_at.desc()).first()

        if removal:
            # Update from adapter result
            removal.method = result.method
            removal.status = result.status
            removal.attempts = result.attempts
            removal.last_error = result.last_error
            removal.recheck_after = result.recheck_after
            removal.confirmed_at = result.confirmed_at
            if result.submitted_at:
                removal.submitted_at = result.submitted_at
        else:
            # Shouldn't happen (API creates it), but handle gracefully
            removal = RemovalRequest(
                listing_id=listing.id,
                user_id=listing.user_id,
                broker=listing.broker,
                method=result.method,
                status=result.status,
                submitted_at=result.submitted_at,
                recheck_after=result.recheck_after,
                attempts=result.attempts,
                last_error=result.last_error,
                confirmed_at=result.confirmed_at,
            )
            db.add(removal)

        # Update listing status to match
        listing.status = result.status
        listing.updated_at = datetime.now(timezone.utc)
        if result.method == "manual":
            listing.removal_method = "manual"
            # Build manual instructions from adapter or error
            listing.manual_instructions = _build_manual_instructions(adapter, result)

        db.commit()
        db.refresh(removal)
        logger.info(
            "Removal submission complete for listing %s: status=%s method=%s",
            listing_id, removal.status, removal.method,
        )
        return str(removal.id)

    except BrokerError as exc:
        logger.warning("BrokerError during removal for listing %s: %s", listing_id, exc)
        removal = db.query(RemovalRequest).filter(
            RemovalRequest.listing_id == listing_id,
            RemovalRequest.status == "removal_sent",
        ).first()

        if exc.reason == "captcha":
            if removal:
                removal.method = "manual"
                removal.status = "failed"
                removal.last_error = exc.message
                removal.attempts = (removal.attempts or 0) + 1
            listing.status = "failed"
            listing.removal_method = "manual"
            listing.manual_instructions = exc.fallback_instructions or (
                f"Automated removal blocked by CAPTCHA. "
                f"Visit {adapter.opt_out_url} and submit your opt-out manually."
            )
        else:
            if removal:
                removal.status = "failed"
                removal.last_error = exc.message
                removal.attempts = (removal.attempts or 0) + 1
            listing.status = "failed"

        listing.updated_at = datetime.now(timezone.utc)
        db.commit()

        # Notify via Telegram
        _send_telegram_removal_failed(db, listing.user_id, listing, exc.message)

        if removal:
            return str(removal.id)
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="ghosted.verify_removal", bind=True, max_retries=0)
def verify_removal_task(self, removal_id: str) -> str:
    """
    Verify whether a removal has been confirmed by the broker.
    Returns the removal_request id.
    """
    logger.info("Starting removal verification for removal %s", removal_id)
    db = SessionLocal()
    try:
        removal = db.query(RemovalRequest).filter(RemovalRequest.id == removal_id).first()
        if not removal:
            logger.error("RemovalRequest %s not found", removal_id)
            raise ValueError(f"RemovalRequest {removal_id} not found")

        adapter = BROKER_REGISTRY.get(removal.broker)
        if not adapter:
            removal.last_error = f"No adapter registered for broker: {removal.broker}"
            removal.attempts = (removal.attempts or 0) + 1
            db.commit()
            raise ValueError(f"No adapter for broker: {removal.broker}")

        # Attach listing URL for the adapter's verify_removal
        listing = db.query(FoundListing).filter(FoundListing.id == removal.listing_id).first()
        if listing:
            removal._listing_url = listing.listing_url

        # Run the async adapter method
        try:
            result = asyncio.get_event_loop().run_until_complete(
                adapter.verify_removal(removal)
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(adapter.verify_removal(removal))
            finally:
                loop.close()

        # Update removal request from result
        removal.status = result.status
        removal.attempts = result.attempts
        removal.last_error = result.last_error
        removal.recheck_after = result.recheck_after
        removal.confirmed_at = result.confirmed_at

        # Update linked listing status to match
        if listing:
            listing.status = result.status
            listing.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(removal)
        logger.info(
            "Removal verification complete for removal %s: status=%s",
            removal_id, removal.status,
        )

        # Send Telegram notification if removal confirmed
        if removal.status == "confirmed" and listing:
            _send_telegram_removal_confirmed(db, removal.user_id, listing)

        return str(removal.id)

    except BrokerError as exc:
        logger.warning("BrokerError during verification for removal %s: %s", removal_id, exc)
        removal = db.query(RemovalRequest).filter(RemovalRequest.id == removal_id).first()
        if removal:
            removal.last_error = exc.message
            removal.attempts = (removal.attempts or 0) + 1
            db.commit()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _send_telegram_removal_confirmed(db: "Session", user_id, listing) -> None:
    """Send Telegram notification for confirmed removal. Silently skip on failure."""
    try:
        user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
        if user and user.telegram_chat_id:
            from app.services.telegram import send_removal_confirmed
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(send_removal_confirmed(user.telegram_chat_id, listing))
            finally:
                loop.close()
    except Exception:
        logger.exception("Failed to send removal-confirmed Telegram notification")


def _send_telegram_removal_failed(db: "Session", user_id, listing, error: str = "") -> None:
    """Send Telegram notification for failed removal. Silently skip on failure."""
    try:
        user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
        if user and user.telegram_chat_id:
            from app.services.telegram import send_removal_failed
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(send_removal_failed(user.telegram_chat_id, listing, error))
            finally:
                loop.close()
    except Exception:
        logger.exception("Failed to send removal-failed Telegram notification")


def _build_manual_instructions(adapter, result) -> str:
    """Build manual instructions string from adapter info and result error."""
    if result.last_error:
        return (
            f"Automated removal failed: {result.last_error}\n"
            f"Please visit {adapter.opt_out_url} and submit your opt-out request manually."
        )
    return f"Please visit {adapter.opt_out_url} and submit your opt-out request manually."
