"""Background scheduler jobs."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from apps.logger import logger
from apps.sqlite.database_operations import DatabaseManager

_scheduler = AsyncIOScheduler()


def _cleanup_old_simulation_sessions() -> None:
    db = DatabaseManager()
    deleted = db.delete_simulation_sessions_older_than(7)
    if deleted:
        logger.info(f"Deleted {deleted} old simulation sessions")


def start_scheduler() -> None:
    """Start the background scheduler if not already running."""
    if _scheduler.running:
        return
    _scheduler.add_job(
        _cleanup_old_simulation_sessions,
        CronTrigger(hour=3, minute=0),
        id="cleanup_simulation_sessions",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Background scheduler started")


def shutdown_scheduler() -> None:
    """Shutdown the background scheduler."""
    if _scheduler.running:
        _scheduler.shutdown()
        logger.info("Background scheduler stopped")
