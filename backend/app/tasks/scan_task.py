"""
Celery task for running a broker scan.
Results are persisted to PostgreSQL by the scan engine (not just Redis).
"""

import logging

from app.services.celery_app import celery_app
from app.services.scan_engine import run_scan_sync

logger = logging.getLogger(__name__)


@celery_app.task(name="ghosted.run_scan", bind=True, max_retries=0)
def run_scan(self, scan_id: str, user_id: str, broker_slugs: list[str] | None = None) -> str:
    """
    Celery task entry point. Delegates to the scan engine.
    Returns the scan_job id.
    """
    logger.info("Starting scan task scan_id=%s for user %s (brokers=%s)", scan_id, user_id, broker_slugs)
    result_id = run_scan_sync(scan_id, user_id, broker_slugs)
    logger.info("Scan task completed: scan_id=%s", result_id)
    return result_id
