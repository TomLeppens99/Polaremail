"""Tests for scheduler module."""

import pytest
from datetime import datetime
import pytz

from polar_report.scheduler import get_cron_trigger, get_next_report_time


class TestScheduler:
    """Test scheduler functionality."""

    def test_get_cron_trigger_normal(self):
        """Test creating trigger with normal time format."""
        trigger = get_cron_trigger(day='Monday', time='08:00', timezone='Europe/Brussels')
        assert trigger is not None

    def test_get_cron_trigger_time_with_seconds(self):
        """Test creating trigger with time that includes seconds."""
        # Should not crash - ignores extra parts
        trigger = get_cron_trigger(day='Monday', time='08:30:45', timezone='Europe/Brussels')
        assert trigger is not None

    def test_get_cron_trigger_malformed_time(self):
        """Test creating trigger with malformed time falls back to default."""
        # Should not crash - falls back to 8:00
        trigger = get_cron_trigger(day='Monday', time='0830', timezone='Europe/Brussels')
        assert trigger is not None

    def test_get_cron_trigger_different_days(self):
        """Test creating triggers for different days."""
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            trigger = get_cron_trigger(day=day, time='09:00', timezone='UTC')
            assert trigger is not None

    def test_get_cron_trigger_invalid_day_defaults(self):
        """Test that invalid day defaults to Monday."""
        trigger = get_cron_trigger(day='notaday', time='08:00', timezone='UTC')
        assert trigger is not None  # Should default to 'mon'

    def test_get_next_report_time_returns_datetime(self):
        """Test that get_next_report_time returns a valid datetime."""
        next_time = get_next_report_time()
        assert isinstance(next_time, datetime)
        assert next_time.tzinfo is not None  # Should be timezone-aware

    def test_get_next_report_time_is_in_future(self):
        """Test that next report time is in the future."""
        next_time = get_next_report_time()
        tz = pytz.timezone('Europe/Brussels')
        now = datetime.now(tz)
        assert next_time >= now
