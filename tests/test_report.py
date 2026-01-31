"""Tests for weekly report generation."""

from datetime import date, datetime

from polar_report.aggregator import TrainingSummary, SleepSummary, RechargeSummary, WeeklyReport
from polar_report.models import Exercise
from polar_report.report import ReportGenerator


def test_generate_plain_text_includes_insights():
    """Ensure insights sections are added when data exists."""
    training = TrainingSummary(
        total_sessions=1,
        total_duration_seconds=3600,
        total_distance_meters=10000,
        total_calories=500
    )
    best_session = Exercise()
    best_session.sport = "RUNNING"
    best_session.duration_seconds = 3600
    best_session.distance_meters = 10000
    best_session.calories = 500
    best_session.average_heart_rate = 150
    best_session.start_time = datetime(2025, 1, 1, 7, 0, 0)
    training.best_session = best_session

    sleep = SleepSummary(
        avg_duration_hours=7.5,
        avg_sleep_score=80,
        best_night_date=date(2025, 1, 2),
        best_night_score=90,
        worst_night_date=date(2025, 1, 3),
        worst_night_score=60
    )

    recovery = RechargeSummary(
        avg_recharge_status=3.5,
        avg_hrv=45,
        best_day_date=date(2025, 1, 2),
        best_day_status=5,
        worst_day_date=date(2025, 1, 3),
        worst_day_status=2,
        low_recharge_days=[
            date(2025, 1, 3),
            date(2025, 1, 4),
            date(2025, 1, 5),
            date(2025, 1, 6)
        ]
    )

    report = WeeklyReport(
        week_start=date(2024, 12, 30),
        week_end=date(2025, 1, 5),
        training=training,
        sleep=sleep,
        recovery=recovery,
        comparison=None,
        highlights=[],
        overall_rating="Good Progress"
    )

    text = ReportGenerator().generate_plain_text(report)

    assert "BEST SESSION" in text
    assert "SLEEP INSIGHTS" in text
    assert "RECOVERY INSIGHTS" in text
    assert "Low Recharge Days" in text
    assert "Running" in text
