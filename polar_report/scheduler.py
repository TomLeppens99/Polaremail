"""
Scheduler for automated weekly report generation.
Uses APScheduler to run reports on configured schedule.
"""

import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import Config
from .email_sender import send_weekly_report
from .polar_api import PolarAPI
from .models import init_db

logger = logging.getLogger(__name__)


# Map day names to cron day values
DAY_MAP = {
    'monday': 'mon',
    'tuesday': 'tue',
    'wednesday': 'wed',
    'thursday': 'thu',
    'friday': 'fri',
    'saturday': 'sat',
    'sunday': 'sun'
}


def get_cron_trigger(day: str = None, time: str = None, timezone: str = None) -> CronTrigger:
    """
    Create a cron trigger for the configured schedule.

    Args:
        day: Day of week (defaults to config)
        time: Time in HH:MM format (defaults to config)
        timezone: Timezone string (defaults to config)

    Returns:
        CronTrigger configured for the schedule
    """
    day = day or Config.REPORT_DAY
    time = time or Config.REPORT_TIME
    timezone = timezone or Config.TIMEZONE

    # Parse time
    hour, minute = time.split(':')

    # Convert day name to cron format
    day_cron = DAY_MAP.get(day.lower(), 'mon')

    return CronTrigger(
        day_of_week=day_cron,
        hour=int(hour),
        minute=int(minute),
        timezone=pytz.timezone(timezone)
    )


def sync_and_report_job():
    """
    Job function that syncs data and sends the weekly report.
    This is the main scheduled task.
    """
    logger.info("Starting scheduled weekly report job")

    try:
        # Ensure database is initialized
        init_db()

        # Sync latest data from Polar API
        if Config.POLAR_ACCESS_TOKEN:
            logger.info("Syncing data from Polar API...")
            api = PolarAPI()
            sync_results = api.sync_all()
            logger.info(f"Sync complete: {sync_results}")
        else:
            logger.warning("No Polar access token - skipping API sync")

        # Generate and send report
        logger.info("Generating and sending weekly report...")
        success = send_weekly_report()

        if success:
            logger.info("Weekly report job completed successfully")
        else:
            logger.error("Weekly report job failed to send email")

    except Exception as e:
        logger.exception(f"Weekly report job failed with error: {e}")


def data_sync_job():
    """
    Job to periodically sync data from Polar API.
    Runs more frequently than the report to keep data fresh.
    """
    logger.info("Starting data sync job")

    try:
        if not Config.POLAR_ACCESS_TOKEN:
            logger.warning("No Polar access token configured - skipping sync")
            return

        api = PolarAPI()
        results = api.sync_all()
        logger.info(f"Data sync complete: {results}")

    except Exception as e:
        logger.exception(f"Data sync job failed: {e}")


class ReportScheduler:
    """Manages scheduled report generation and data syncing."""

    def __init__(self, blocking: bool = True):
        """
        Initialize the scheduler.

        Args:
            blocking: Use blocking scheduler (True) or background (False)
        """
        if blocking:
            self.scheduler = BlockingScheduler(timezone=Config.TIMEZONE)
        else:
            self.scheduler = BackgroundScheduler(timezone=Config.TIMEZONE)

        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Set up graceful shutdown handlers."""
        def shutdown_handler(signum, frame):
            logger.info("Received shutdown signal, stopping scheduler...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

    def add_weekly_report_job(self, day: str = None, time: str = None):
        """
        Add the weekly report job to the scheduler.

        Args:
            day: Day of week to run (defaults to config)
            time: Time to run in HH:MM format (defaults to config)
        """
        trigger = get_cron_trigger(day=day, time=time)

        self.scheduler.add_job(
            sync_and_report_job,
            trigger=trigger,
            id='weekly_report',
            name='Weekly Training Report',
            replace_existing=True,
            misfire_grace_time=3600  # Allow 1 hour grace period for misfires
        )

        day = day or Config.REPORT_DAY
        time = time or Config.REPORT_TIME
        logger.info(f"Weekly report job scheduled for {day} at {time} ({Config.TIMEZONE})")

    def add_daily_sync_job(self, hour: int = 3, minute: int = 0):
        """
        Add daily data sync job to keep database updated.

        Args:
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
        """
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone=pytz.timezone(Config.TIMEZONE)
        )

        self.scheduler.add_job(
            data_sync_job,
            trigger=trigger,
            id='daily_sync',
            name='Daily Data Sync',
            replace_existing=True,
            misfire_grace_time=3600
        )

        logger.info(f"Daily sync job scheduled for {hour:02d}:{minute:02d}")

    def start(self):
        """Start the scheduler."""
        logger.info("Starting scheduler...")

        # Print scheduled jobs
        jobs = self.scheduler.get_jobs()
        if jobs:
            logger.info(f"Scheduled jobs ({len(jobs)}):")
            for job in jobs:
                logger.info(f"  - {job.name}: next run at {job.next_run_time}")
        else:
            logger.warning("No jobs scheduled!")

        self.scheduler.start()

    def stop(self):
        """Stop the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")

    def run_now(self):
        """Manually trigger the weekly report immediately."""
        logger.info("Manually triggering weekly report...")
        sync_and_report_job()


def run_scheduler():
    """
    Main entry point to run the scheduler.
    Starts both the weekly report and daily sync jobs.
    """
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize database
    init_db()

    # Create and configure scheduler
    scheduler = ReportScheduler(blocking=True)
    scheduler.add_weekly_report_job()
    scheduler.add_daily_sync_job()

    # Start scheduler (blocks)
    print(f"\nPolar Weekly Report Scheduler")
    print(f"=" * 40)
    print(f"Report Schedule: {Config.REPORT_DAY} at {Config.REPORT_TIME}")
    print(f"Timezone: {Config.TIMEZONE}")
    print(f"Email recipient: {Config.EMAIL_RECIPIENT}")
    print(f"\nPress Ctrl+C to stop\n")

    scheduler.start()


def get_next_report_time() -> datetime:
    """
    Calculate when the next report will be sent.

    Returns:
        datetime of next scheduled report
    """
    tz = pytz.timezone(Config.TIMEZONE)
    now = datetime.now(tz)

    # Parse configured time
    hour, minute = map(int, Config.REPORT_TIME.split(':'))

    # Get configured day
    day_name = Config.REPORT_DAY.lower()
    day_numbers = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2,
        'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
    }
    target_day = day_numbers.get(day_name, 0)

    # Calculate days until next occurrence
    days_ahead = target_day - now.weekday()
    if days_ahead < 0:  # Target day already passed this week
        days_ahead += 7
    elif days_ahead == 0:  # Same day
        # Check if time has passed
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now >= target_time:
            days_ahead = 7

    next_report = now + timedelta(days=days_ahead)
    next_report = next_report.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return next_report


if __name__ == '__main__':
    run_scheduler()
