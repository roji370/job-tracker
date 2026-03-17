"""
APScheduler setup — runs pipeline every 6 hours.
Fix #5: Only safe with --workers 1 (see Dockerfile).
Fix #20: Retry logic on transient DB failures using tenacity.
"""
import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.services.pipeline import run_pipeline

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=30, max=300),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=False,
)
async def _run_pipeline_with_retry() -> None:
    """Run the pipeline with up to 3 retries on failure (exponential back-off)."""
    async with AsyncSessionLocal() as db:
        result = await run_pipeline(db, triggered_by="scheduler")
        logger.info("✅ Pipeline completed: %s", result)


async def scheduled_pipeline_job():
    """Task wrapper for APScheduler — handles exceptions so the job doesn't die."""
    logger.info("⏰ Scheduler triggered pipeline run...")
    try:
        await _run_pipeline_with_retry()
    except Exception as e:
        # All retries exhausted — log but don't crash the scheduler
        logger.error("❌ Scheduled pipeline failed after all retries: %s", e)


def start_scheduler():
    """Start the background scheduler."""
    interval_hours = settings.SCHEDULER_INTERVAL_HOURS
    scheduler.add_job(
        scheduled_pipeline_job,
        trigger=IntervalTrigger(hours=interval_hours),
        id="pipeline_job",
        name="Job Scrape + Match Pipeline",
        replace_existing=True,
        max_instances=1,  # Prevents overlapping runs even if one takes > interval_hours
    )
    scheduler.start()
    logger.info("🕐 Scheduler started — runs every %d hour(s)", interval_hours)


def stop_scheduler():
    """Gracefully stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
