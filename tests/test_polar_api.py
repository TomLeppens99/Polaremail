"""Tests for Polar API module."""

import pytest
from polar_report.polar_api import PolarAPI


class TestPolarAPI:
    """Test PolarAPI class functionality."""

    def test_parse_iso_duration_full(self):
        """Test parsing duration with hours, minutes, seconds."""
        assert PolarAPI.parse_iso_duration('PT1H30M45S') == 5445

    def test_parse_iso_duration_hours_only(self):
        """Test parsing duration with hours only."""
        assert PolarAPI.parse_iso_duration('PT2H') == 7200

    def test_parse_iso_duration_minutes_only(self):
        """Test parsing duration with minutes only."""
        assert PolarAPI.parse_iso_duration('PT45M') == 2700

    def test_parse_iso_duration_seconds_only(self):
        """Test parsing duration with seconds only."""
        assert PolarAPI.parse_iso_duration('PT30S') == 30

    def test_parse_iso_duration_hours_minutes(self):
        """Test parsing duration with hours and minutes."""
        assert PolarAPI.parse_iso_duration('PT1H15M') == 4500

    def test_parse_iso_duration_empty(self):
        """Test parsing empty duration."""
        assert PolarAPI.parse_iso_duration('') == 0
        assert PolarAPI.parse_iso_duration(None) == 0

    def test_parse_iso_duration_invalid(self):
        """Test parsing invalid duration format."""
        assert PolarAPI.parse_iso_duration('invalid') == 0

    def test_parse_iso_duration_decimal_seconds(self):
        """Test parsing duration with decimal seconds."""
        result = PolarAPI.parse_iso_duration('PT1M30.5S')
        assert result == 90  # Truncated to int
