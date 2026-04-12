"""Background scheduler jobs."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.common.logger import logger
from backend.db.sqlite.database_operations import DatabaseManager

_scheduler = AsyncIOScheduler()


def _cleanup_old_simulation_sessions() -> None:
    db = DatabaseManager()
    deleted = db.delete_simulation_sessions_older_than(7)
    if deleted:
        logger.info(f"Deleted {deleted} old simulation sessions")


def _refresh_edge_lab_universe() -> None:
    try:
        from backend.api.legacy.routes.edge import run_scheduled_edge_lab_refresh

        result = run_scheduled_edge_lab_refresh()
        if result.get("status") != "skipped":
            logger.info(f"Edge Lab scheduled refresh completed: {result.get('run_count', 0)} runs")
    except Exception as exc:
        logger.error(f"Edge Lab scheduled refresh failed: {exc}")


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
    _scheduler.add_job(
        _refresh_edge_lab_universe,
        CronTrigger(hour=4, minute=0),
        id="refresh_edge_lab_universe",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Background scheduler started")


def shutdown_scheduler() -> None:
    """Shutdown the background scheduler."""
    if _scheduler.running:
        _scheduler.shutdown()
        logger.info("Background scheduler stopped")

