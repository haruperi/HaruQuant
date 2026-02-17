"""
Scheduler Utilities Usage Examples

Purpose:
- Demonstrate background job scheduling with APScheduler
- Show how to schedule periodic cleanup tasks
- Illustrate startup and shutdown of the scheduler
- Examples for cron-based job scheduling

Key Concepts:
- AsyncIO-based background scheduler
- Cron triggers for scheduled tasks
- Automatic cleanup of old simulation sessions
- Integration with FastAPI lifecycle events

Note:
    The scheduler requires an asyncio event loop to run (provided by FastAPI).
    These examples demonstrate the concepts and usage patterns.
    In production, the scheduler runs automatically when the FastAPI server starts.

Usage:
    python tests/usage/utils/usage_scheduler.py
"""

import sys
from pathlib import Path
import time
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.utils.scheduler import start_scheduler, shutdown_scheduler
from apps.utils.logger import logger


def example_01_basic_scheduler_usage():
    """Example 1: Basic scheduler startup and shutdown."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Basic Scheduler Usage")
    logger.info("=" * 70)

    logger.info("In production (with FastAPI event loop):")
    logger.info("  start_scheduler()")
    logger.info("  # Scheduler is now running")
    logger.info("")
    logger.info("The scheduler is configured to run cleanup jobs at 3:00 AM daily")
    logger.info("Job: cleanup_simulation_sessions")
    logger.info("  - Deletes simulation sessions older than 7 days")
    logger.info("  - Runs every day at 3:00 AM")
    logger.info("")
    logger.info("On shutdown:")
    logger.info("  shutdown_scheduler()")
    logger.info("  # Scheduler has been stopped")
    logger.info("")
    logger.info("Note: Scheduler requires asyncio event loop (provided by FastAPI)")


def example_02_idempotent_start():
    """Example 2: Demonstrate that starting an already running scheduler is safe."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 2: Idempotent Start")
    logger.info("=" * 70)

    logger.info("The scheduler checks if it's already running before starting:")
    logger.info("")
    logger.info("  if _scheduler.running:")
    logger.info("      return  # Already running, do nothing")
    logger.info("")
    logger.info("This means you can safely call start_scheduler() multiple times")
    logger.info("without creating duplicate jobs or errors.")
    logger.info("")
    logger.info("Example:")
    logger.info("  start_scheduler()  # Starts the scheduler")
    logger.info("  start_scheduler()  # No-op, already running")
    logger.info("  start_scheduler()  # No-op, already running")


def example_03_understanding_cron_schedule():
    """Example 3: Understanding the cron schedule configuration."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 3: Understanding Cron Schedule")
    logger.info("=" * 70)

    logger.info("The scheduler uses APScheduler's CronTrigger")
    logger.info("Current configuration: CronTrigger(hour=3, minute=0)")
    logger.info("")
    logger.info("This means:")
    logger.info("  - Runs every day")
    logger.info("  - At 3:00 AM (03:00)")
    logger.info("  - In the server's local timezone")
    logger.info("")
    logger.info("Other cron examples:")
    logger.info("  - Every hour: CronTrigger(minute=0)")
    logger.info("  - Every 30 minutes: CronTrigger(minute='*/30')")
    logger.info("  - Weekdays at noon: CronTrigger(day_of_week='mon-fri', hour=12)")
    logger.info("  - First day of month: CronTrigger(day=1, hour=0, minute=0)")


def example_04_scheduled_cleanup_job():
    """Example 4: What the scheduled cleanup job does."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 4: Scheduled Cleanup Job")
    logger.info("=" * 70)

    logger.info("Job Name: cleanup_simulation_sessions")
    logger.info("Job ID: cleanup_simulation_sessions")
    logger.info("Schedule: Daily at 3:00 AM")
    logger.info("")
    logger.info("Job Function: _cleanup_old_simulation_sessions()")
    logger.info("What it does:")
    logger.info("  1. Connects to the database")
    logger.info("  2. Calls delete_simulation_sessions_older_than(7)")
    logger.info("  3. Deletes simulation sessions older than 7 days")
    logger.info("  4. Logs the number of deleted sessions")
    logger.info("")
    logger.info("This prevents the database from growing too large with old simulation data")


def example_05_fastapi_integration():
    """Example 5: Integration with FastAPI lifecycle."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 5: FastAPI Integration")
    logger.info("=" * 70)

    logger.info("The scheduler is integrated with FastAPI's lifecycle events:")
    logger.info("")
    logger.info("On Startup (@app.on_event('startup')):")
    logger.info("  from apps.utils.scheduler import start_scheduler")
    logger.info("  start_scheduler()")
    logger.info("")
    logger.info("On Shutdown (@app.on_event('shutdown')):")
    logger.info("  from apps.utils.scheduler import shutdown_scheduler")
    logger.info("  shutdown_scheduler()")
    logger.info("")
    logger.info("This ensures:")
    logger.info("  - Scheduler starts when API server starts")
    logger.info("  - Scheduler stops gracefully when API server stops")
    logger.info("  - No orphaned background jobs")


def example_06_manual_cleanup_test():
    """Example 6: Test the cleanup function manually (without scheduler)."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 6: Manual Cleanup Test")
    logger.info("=" * 70)

    logger.info("Testing the cleanup function directly...")
    logger.info("This would normally run at 3:00 AM via the scheduler")
    logger.info("")

    try:
        from apps.sqlite.database_operations import DatabaseManager

        db = DatabaseManager()
        deleted = db.delete_simulation_sessions_older_than(7)

        logger.info(f"Cleanup completed successfully")
        logger.info(f"Deleted {deleted} simulation sessions older than 7 days")

        if deleted == 0:
            logger.info("(No old sessions to delete)")

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")


def example_07_scheduler_state_check():
    """Example 7: Check scheduler state."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 7: Scheduler State Check")
    logger.info("=" * 70)

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apps.utils import scheduler as scheduler_module

    scheduler_instance = scheduler_module._scheduler

    logger.info(f"Scheduler type: {type(scheduler_instance).__name__}")
    logger.info(f"Scheduler running: {scheduler_instance.running}")
    logger.info("")
    logger.info("When running (in FastAPI), you can check scheduled jobs:")
    logger.info("")
    logger.info("  jobs = _scheduler.get_jobs()")
    logger.info("  for job in jobs:")
    logger.info("      print(f'Job: {job.id}')")
    logger.info("      print(f'Next run: {job.next_run_time}')")
    logger.info("")
    logger.info("Current jobs configured:")
    logger.info("  - cleanup_simulation_sessions (daily at 3:00 AM)")


def example_08_custom_schedule_pattern():
    """Example 8: How to add custom scheduled jobs (conceptual)."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 8: Custom Schedule Pattern (Conceptual)")
    logger.info("=" * 70)

    logger.info("To add custom scheduled jobs, you would modify scheduler.py:")
    logger.info("")
    logger.info("1. Define your job function:")
    logger.info("   def _my_custom_job():")
    logger.info("       # Your job logic here")
    logger.info("       pass")
    logger.info("")
    logger.info("2. Add the job in start_scheduler():")
    logger.info("   _scheduler.add_job(")
    logger.info("       _my_custom_job,")
    logger.info("       CronTrigger(hour=12, minute=0),  # Run at noon")
    logger.info("       id='my_custom_job',")
    logger.info("       replace_existing=True,")
    logger.info("   )")
    logger.info("")
    logger.info("Common scheduling patterns:")
    logger.info("  - Every hour: CronTrigger(minute=0)")
    logger.info("  - Every 15 minutes: CronTrigger(minute='*/15')")
    logger.info("  - Business hours: CronTrigger(hour='9-17', minute=0)")
    logger.info("  - Weekends: CronTrigger(day_of_week='sat,sun', hour=10)")


def example_09_scheduler_benefits():
    """Example 9: Benefits of using the scheduler."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 9: Scheduler Benefits")
    logger.info("=" * 70)

    logger.info("Benefits of using APScheduler for background jobs:")
    logger.info("")
    logger.info("1. Automatic Execution")
    logger.info("   - Jobs run on schedule without manual intervention")
    logger.info("   - No need for external cron jobs")
    logger.info("")
    logger.info("2. AsyncIO Integration")
    logger.info("   - Works seamlessly with FastAPI's async framework")
    logger.info("   - Non-blocking execution")
    logger.info("")
    logger.info("3. Persistent Scheduling")
    logger.info("   - Schedules persist across application restarts")
    logger.info("   - Jobs can be added/removed dynamically")
    logger.info("")
    logger.info("4. Error Handling")
    logger.info("   - Failed jobs don't crash the scheduler")
    logger.info("   - Jobs continue on schedule even if one fails")
    logger.info("")
    logger.info("5. Flexibility")
    logger.info("   - Support for cron, interval, and date triggers")
    logger.info("   - Easy to add new jobs")
    logger.info("")
    logger.info("6. Database Maintenance")
    logger.info("   - Automatic cleanup of old data")
    logger.info("   - Prevents database bloat")


def example_10_production_considerations():
    """Example 10: Production deployment considerations."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 10: Production Considerations")
    logger.info("=" * 70)

    logger.info("Important considerations for production deployment:")
    logger.info("")
    logger.info("1. Timezone Awareness")
    logger.info("   - Ensure server timezone is correctly set")
    logger.info("   - Consider using UTC for consistency")
    logger.info("   - Document expected timezone in code comments")
    logger.info("")
    logger.info("2. Job Execution Time")
    logger.info("   - Choose off-peak hours (3:00 AM is typical)")
    logger.info("   - Consider time zones of your users")
    logger.info("   - Monitor job execution duration")
    logger.info("")
    logger.info("3. Error Handling")
    logger.info("   - Jobs should handle exceptions gracefully")
    logger.info("   - Log all job execution results")
    logger.info("   - Consider implementing retry logic")
    logger.info("")
    logger.info("4. Resource Usage")
    logger.info("   - Cleanup jobs should be efficient")
    logger.info("   - Monitor database performance during cleanup")
    logger.info("   - Consider batch deletion for large datasets")
    logger.info("")
    logger.info("5. Monitoring")
    logger.info("   - Log job start and completion times")
    logger.info("   - Track number of items processed")
    logger.info("   - Set up alerts for job failures")
    logger.info("")
    logger.info("6. Single Instance")
    logger.info("   - Ensure only one scheduler runs if using multiple servers")
    logger.info("   - Consider using distributed locking")
    logger.info("   - Or designate one server for scheduled jobs")


def main():
    """Run all scheduler utility examples."""
    logger.info("\n" + "=" * 80)
    logger.info("SCHEDULER UTILITIES - COMPREHENSIVE USAGE EXAMPLES")
    logger.info("=" * 80)

    example_01_basic_scheduler_usage()
    example_02_idempotent_start()
    example_03_understanding_cron_schedule()
    example_04_scheduled_cleanup_job()
    example_05_fastapi_integration()
    example_06_manual_cleanup_test()
    example_07_scheduler_state_check()
    example_08_custom_schedule_pattern()
    example_09_scheduler_benefits()
    example_10_production_considerations()

    logger.info("\n" + "=" * 80)
    logger.info("ALL EXAMPLES COMPLETED")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

