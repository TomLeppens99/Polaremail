"""
Polar Weekly Training Report System

An automated system that fetches Polar fitness data via the Accesslink API
and generates comprehensive weekly email reports.

Usage:
    python -m polar_report auth      # Authenticate with Polar
    python -m polar_report sync      # Sync data from API
    python -m polar_report report    # Generate weekly report
    python -m polar_report schedule  # Run scheduled jobs
    python -m polar_report status    # Show system status
"""

__version__ = '1.0.0'
__author__ = 'Polar Weekly Report'

from .config import Config
from .models import (
    init_db,
    get_session,
    Exercise,
    SleepRecord,
    NightlyRecharge,
    ActivitySummary
)
from .auth import PolarAuth, PolarAuthError
from .polar_api import PolarAPI, PolarAPIError
from .aggregator import WeeklyAggregator, WeeklyReport
from .report import ReportGenerator, generate_weekly_report
from .email_sender import EmailSender, send_weekly_report
from .scheduler import ReportScheduler, run_scheduler

__all__ = [
    # Configuration
    'Config',

    # Database
    'init_db',
    'get_session',
    'Exercise',
    'SleepRecord',
    'NightlyRecharge',
    'ActivitySummary',

    # Authentication
    'PolarAuth',
    'PolarAuthError',

    # API
    'PolarAPI',
    'PolarAPIError',

    # Aggregation & Reporting
    'WeeklyAggregator',
    'WeeklyReport',
    'ReportGenerator',
    'generate_weekly_report',

    # Email
    'EmailSender',
    'send_weekly_report',

    # Scheduling
    'ReportScheduler',
    'run_scheduler',
]
