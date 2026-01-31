"""Tests for data aggregation module."""

import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock

from polar_report.aggregator import (
    WeeklyAggregator,
    TrainingSummary,
    SleepSummary,
    RechargeSummary,
    HeartRateZoneData,
    format_duration,
    format_distance
)


class TestHeartRateZoneData:
    """Test HeartRateZoneData dataclass."""

    def test_total_seconds(self):
        """Test total seconds calculation."""
        zones = HeartRateZoneData(
            zone1_seconds=100,
            zone2_seconds=200,
            zone3_seconds=300,
            zone4_seconds=150,
            zone5_seconds=50
        )
        assert zones.total_seconds == 800

    def test_get_percentages(self):
        """Test percentage calculation."""
        zones = HeartRateZoneData(
            zone1_seconds=100,
            zone2_seconds=200,
            zone3_seconds=200,
            zone4_seconds=300,
            zone5_seconds=200
        )
        pcts = zones.get_percentages()
        assert pcts['zone1'] == 10.0
        assert pcts['zone2'] == 20.0
        assert pcts['zone5'] == 20.0

    def test_get_percentages_empty(self):
        """Test percentage calculation with no data."""
        zones = HeartRateZoneData()
        pcts = zones.get_percentages()
        for zone in ['zone1', 'zone2', 'zone3', 'zone4', 'zone5']:
            assert pcts[zone] == 0.0


class TestFormatFunctions:
    """Test formatting functions."""

    def test_format_duration_seconds(self):
        """Test formatting short durations."""
        assert format_duration(45) == "45s"

    def test_format_duration_minutes(self):
        """Test formatting minute durations."""
        assert format_duration(300) == "5min"
        assert format_duration(90) == "1min"

    def test_format_duration_hours(self):
        """Test formatting hour durations."""
        assert format_duration(3600) == "1h 0min"
        assert format_duration(5400) == "1h 30min"

    def test_format_distance_short(self):
        """Test formatting short distances."""
        assert format_distance(500) == "0.50 km"
        assert format_distance(5000) == "5.00 km"

    def test_format_distance_long(self):
        """Test formatting long distances."""
        assert format_distance(15000) == "15.0 km"
        assert format_distance(42195) == "42.2 km"


class TestWeeklyAggregator:
    """Test WeeklyAggregator class."""

    def test_get_week_dates_default(self):
        """Test getting last week's dates."""
        aggregator = WeeklyAggregator(user_id='test')
        start, end = aggregator.get_week_dates()
        
        # Should always be Monday to Sunday
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 6    # Sunday
        assert (end - start).days == 6

    def test_get_week_dates_specific(self):
        """Test getting dates for a specific week."""
        aggregator = WeeklyAggregator(user_id='test')
        ref_date = date(2025, 1, 15)  # Wednesday
        start, end = aggregator.get_week_dates(ref_date)
        
        assert start == date(2025, 1, 13)  # Monday of that week
        assert end == date(2025, 1, 19)    # Sunday of that week

    def test_aggregate_training_empty(self):
        """Test aggregating empty exercise list."""
        aggregator = WeeklyAggregator(user_id='test')
        summary = aggregator.aggregate_training([])
        
        assert summary.total_sessions == 0
        assert summary.total_duration_seconds == 0
        assert summary.total_calories == 0

    def test_aggregate_sleep_empty(self):
        """Test aggregating empty sleep list."""
        aggregator = WeeklyAggregator(user_id='test')
        summary = aggregator.aggregate_sleep([])
        
        assert summary.total_nights == 0
        assert summary.avg_duration_hours == 0

    def test_aggregate_recovery_empty(self):
        """Test aggregating empty recovery list."""
        aggregator = WeeklyAggregator(user_id='test')
        summary = aggregator.aggregate_recovery([])
        
        assert summary.total_days == 0
        assert summary.avg_recharge_status is None

    def test_determine_overall_rating_no_data(self):
        """Test rating determination with no data."""
        aggregator = WeeklyAggregator(user_id='test')
        
        training = TrainingSummary()
        sleep = SleepSummary()
        recovery = RechargeSummary()
        
        rating = aggregator.determine_overall_rating(training, sleep, recovery, [])
        assert rating == "Take It Easy"
