"""
Data aggregation and analysis for weekly reports.
Calculates metrics, comparisons, and generates insights from stored data.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import statistics

from .models import (
    get_session, Exercise, SleepRecord, NightlyRecharge,
    get_exercises_in_range, get_sleep_in_range, get_recharge_in_range
)
from .config import Config


@dataclass
class SportBreakdown:
    """Training breakdown for a specific sport."""
    sport: str
    session_count: int = 0
    total_duration_seconds: int = 0
    total_distance_meters: float = 0
    total_calories: int = 0
    avg_heart_rate: Optional[float] = None


@dataclass
class HeartRateZoneData:
    """Heart rate zone distribution data."""
    zone1_seconds: int = 0  # Recovery
    zone2_seconds: int = 0  # Light
    zone3_seconds: int = 0  # Moderate
    zone4_seconds: int = 0  # Hard
    zone5_seconds: int = 0  # Maximum

    @property
    def total_seconds(self) -> int:
        return (self.zone1_seconds + self.zone2_seconds + self.zone3_seconds +
                self.zone4_seconds + self.zone5_seconds)

    def get_percentages(self) -> Dict[str, float]:
        """Get percentage distribution across zones."""
        total = self.total_seconds
        if total == 0:
            return {f'zone{i}': 0.0 for i in range(1, 6)}

        return {
            'zone1': round(self.zone1_seconds / total * 100, 1),
            'zone2': round(self.zone2_seconds / total * 100, 1),
            'zone3': round(self.zone3_seconds / total * 100, 1),
            'zone4': round(self.zone4_seconds / total * 100, 1),
            'zone5': round(self.zone5_seconds / total * 100, 1),
        }


@dataclass
class SleepSummary:
    """Sleep quality summary for a period."""
    total_nights: int = 0
    avg_duration_hours: float = 0
    avg_sleep_score: Optional[float] = None
    avg_deep_sleep_hours: float = 0
    avg_rem_sleep_hours: float = 0
    avg_light_sleep_hours: float = 0
    best_night_date: Optional[date] = None
    best_night_score: Optional[float] = None
    worst_night_date: Optional[date] = None
    worst_night_score: Optional[float] = None


@dataclass
class RechargeSummary:
    """Nightly Recharge (recovery) summary for a period."""
    total_days: int = 0
    avg_recharge_status: Optional[float] = None
    avg_ans_charge: Optional[float] = None
    avg_hrv: Optional[float] = None
    best_day_date: Optional[date] = None
    best_day_status: Optional[int] = None
    worst_day_date: Optional[date] = None
    worst_day_status: Optional[int] = None
    low_recharge_days: List[date] = field(default_factory=list)  # Days with status <= 2


@dataclass
class TrainingSummary:
    """Training summary for a period."""
    total_sessions: int = 0
    total_duration_seconds: int = 0
    total_distance_meters: float = 0
    total_calories: int = 0
    avg_heart_rate: Optional[float] = None
    max_heart_rate: Optional[int] = None
    avg_cardio_load: Optional[float] = None
    avg_muscle_load: Optional[float] = None
    total_cardio_load: float = 0
    total_muscle_load: float = 0
    hr_zones: HeartRateZoneData = field(default_factory=HeartRateZoneData)
    sport_breakdown: Dict[str, SportBreakdown] = field(default_factory=dict)
    best_session: Optional[Exercise] = None


@dataclass
class WeeklyComparison:
    """Comparison between two weeks."""
    current_sessions: int
    previous_sessions: int
    session_change_percent: float

    current_duration_hours: float
    previous_duration_hours: float
    duration_change_percent: float

    current_distance_km: float
    previous_distance_km: float
    distance_change_percent: float

    current_calories: int
    previous_calories: int
    calories_change_percent: float

    current_sleep_score: Optional[float]
    previous_sleep_score: Optional[float]
    sleep_score_change: Optional[float]

    current_recharge: Optional[float]
    previous_recharge: Optional[float]
    recharge_change: Optional[float]


@dataclass
class Highlight:
    """Achievement or concern highlight."""
    type: str  # 'achievement' or 'concern'
    icon: str
    message: str
    details: Optional[str] = None


@dataclass
class WeeklyReport:
    """Complete weekly report data."""
    week_start: date
    week_end: date
    training: TrainingSummary
    sleep: SleepSummary
    recovery: RechargeSummary
    comparison: Optional[WeeklyComparison]
    highlights: List[Highlight]
    overall_rating: str  # 'Great Week!', 'Good Progress', 'Needs Attention', 'Take It Easy'


class WeeklyAggregator:
    """Aggregates data for weekly report generation."""

    # Recharge status labels
    RECHARGE_STATUS = {
        1: 'Very Poor',
        2: 'Poor',
        3: 'Compromised',
        4: 'Good',
        5: 'Very Good'
    }

    def __init__(self, user_id: str = None):
        """
        Initialize aggregator.

        Args:
            user_id: Polar user ID (defaults to config)
        """
        self.user_id = user_id or Config.POLAR_USER_ID

    def get_week_dates(self, reference_date: date = None) -> Tuple[date, date]:
        """
        Get the start and end dates for the week.
        Week runs Monday to Sunday.

        Args:
            reference_date: Date to calculate week for (defaults to last week)

        Returns:
            Tuple of (week_start, week_end)
        """
        if reference_date is None:
            # Default to last completed week (Monday to Sunday)
            today = date.today()

            # Find the Monday of the current week
            days_since_monday = today.weekday()  # Monday=0, Sunday=6
            current_week_monday = today - timedelta(days=days_since_monday)

            # Last completed week is the week before current week
            week_start = current_week_monday - timedelta(days=7)
            week_end = week_start + timedelta(days=6)
        else:
            # Get Monday of the specified week
            days_since_monday = reference_date.weekday()
            week_start = reference_date - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)

        return week_start, week_end

    def aggregate_training(self, exercises: List[Exercise]) -> TrainingSummary:
        """
        Aggregate training data from exercises.

        Args:
            exercises: List of Exercise records

        Returns:
            TrainingSummary with aggregated data
        """
        summary = TrainingSummary()

        if not exercises:
            return summary

        summary.total_sessions = len(exercises)

        heart_rates = []
        max_hrs = []
        cardio_loads = []
        muscle_loads = []
        sport_data = defaultdict(lambda: SportBreakdown(sport=''))

        best_session = None
        best_score = 0

        for ex in exercises:
            # Basic totals
            summary.total_duration_seconds += ex.duration_seconds or 0
            summary.total_distance_meters += ex.distance_meters or 0
            summary.total_calories += ex.calories or 0

            # Heart rate
            if ex.average_heart_rate:
                heart_rates.append(ex.average_heart_rate)
            if ex.max_heart_rate:
                max_hrs.append(ex.max_heart_rate)

            # Training load
            if ex.training_load_cardio:
                cardio_loads.append(ex.training_load_cardio)
                summary.total_cardio_load += ex.training_load_cardio
            if ex.training_load_muscle:
                muscle_loads.append(ex.training_load_muscle)
                summary.total_muscle_load += ex.training_load_muscle

            # HR zones
            if ex.heart_rate_zones:
                zones = ex.heart_rate_zones
                summary.hr_zones.zone1_seconds += zones.get('zone1', 0)
                summary.hr_zones.zone2_seconds += zones.get('zone2', 0)
                summary.hr_zones.zone3_seconds += zones.get('zone3', 0)
                summary.hr_zones.zone4_seconds += zones.get('zone4', 0)
                summary.hr_zones.zone5_seconds += zones.get('zone5', 0)

            # Sport breakdown
            sport = ex.sport or 'Unknown'
            if sport not in sport_data:
                sport_data[sport] = SportBreakdown(sport=sport)

            sport_data[sport].session_count += 1
            sport_data[sport].total_duration_seconds += ex.duration_seconds or 0
            sport_data[sport].total_distance_meters += ex.distance_meters or 0
            sport_data[sport].total_calories += ex.calories or 0

            # Determine best session (by duration + load combination)
            session_score = (ex.duration_seconds or 0) / 60
            if ex.training_load_cardio:
                session_score += ex.training_load_cardio * 2
            if session_score > best_score:
                best_score = session_score
                best_session = ex

        # Calculate averages
        if heart_rates:
            summary.avg_heart_rate = statistics.mean(heart_rates)
        if max_hrs:
            summary.max_heart_rate = max(max_hrs)
        if cardio_loads:
            summary.avg_cardio_load = statistics.mean(cardio_loads)
        if muscle_loads:
            summary.avg_muscle_load = statistics.mean(muscle_loads)

        summary.sport_breakdown = dict(sport_data)
        summary.best_session = best_session

        return summary

    def aggregate_sleep(self, sleep_records: List[SleepRecord]) -> SleepSummary:
        """
        Aggregate sleep data.

        Args:
            sleep_records: List of SleepRecord records

        Returns:
            SleepSummary with aggregated data
        """
        summary = SleepSummary()

        if not sleep_records:
            return summary

        summary.total_nights = len(sleep_records)

        durations = []
        scores = []
        deep_sleeps = []
        rem_sleeps = []
        light_sleeps = []

        best_record = None
        worst_record = None

        for record in sleep_records:
            if record.duration_seconds:
                durations.append(record.duration_seconds / 3600)  # Convert to hours

            if record.sleep_score is not None:
                scores.append(record.sleep_score)
                if best_record is None or record.sleep_score > best_record.sleep_score:
                    best_record = record
                if worst_record is None or record.sleep_score < worst_record.sleep_score:
                    worst_record = record

            if record.deep_sleep_seconds:
                deep_sleeps.append(record.deep_sleep_seconds / 3600)
            if record.rem_sleep_seconds:
                rem_sleeps.append(record.rem_sleep_seconds / 3600)
            if record.light_sleep_seconds:
                light_sleeps.append(record.light_sleep_seconds / 3600)

        # Calculate averages
        if durations:
            summary.avg_duration_hours = statistics.mean(durations)
        if scores:
            summary.avg_sleep_score = statistics.mean(scores)
        if deep_sleeps:
            summary.avg_deep_sleep_hours = statistics.mean(deep_sleeps)
        if rem_sleeps:
            summary.avg_rem_sleep_hours = statistics.mean(rem_sleeps)
        if light_sleeps:
            summary.avg_light_sleep_hours = statistics.mean(light_sleeps)

        if best_record:
            summary.best_night_date = best_record.sleep_date
            summary.best_night_score = best_record.sleep_score
        if worst_record:
            summary.worst_night_date = worst_record.sleep_date
            summary.worst_night_score = worst_record.sleep_score

        return summary

    def aggregate_recovery(self, recharge_records: List[NightlyRecharge]) -> RechargeSummary:
        """
        Aggregate nightly recharge/recovery data.

        Args:
            recharge_records: List of NightlyRecharge records

        Returns:
            RechargeSummary with aggregated data
        """
        summary = RechargeSummary()

        if not recharge_records:
            return summary

        summary.total_days = len(recharge_records)

        statuses = []
        ans_charges = []
        hrvs = []

        best_record = None
        worst_record = None

        for record in recharge_records:
            if record.nightly_recharge_status is not None:
                statuses.append(record.nightly_recharge_status)

                if record.nightly_recharge_status <= 2:
                    summary.low_recharge_days.append(record.recharge_date)

                if best_record is None or record.nightly_recharge_status > best_record.nightly_recharge_status:
                    best_record = record
                if worst_record is None or record.nightly_recharge_status < worst_record.nightly_recharge_status:
                    worst_record = record

            if record.ans_charge is not None:
                ans_charges.append(record.ans_charge)
            if record.hrv_avg is not None:
                hrvs.append(record.hrv_avg)

        # Calculate averages
        if statuses:
            summary.avg_recharge_status = statistics.mean(statuses)
        if ans_charges:
            summary.avg_ans_charge = statistics.mean(ans_charges)
        if hrvs:
            summary.avg_hrv = statistics.mean(hrvs)

        if best_record:
            summary.best_day_date = best_record.recharge_date
            summary.best_day_status = best_record.nightly_recharge_status
        if worst_record:
            summary.worst_day_date = worst_record.recharge_date
            summary.worst_day_status = worst_record.nightly_recharge_status

        return summary

    def calculate_comparison(
        self,
        current: TrainingSummary,
        previous: TrainingSummary,
        current_sleep: SleepSummary,
        previous_sleep: SleepSummary,
        current_recovery: RechargeSummary,
        previous_recovery: RechargeSummary
    ) -> WeeklyComparison:
        """
        Calculate week-over-week comparison.

        Args:
            current: Current week training summary
            previous: Previous week training summary
            current_sleep: Current week sleep summary
            previous_sleep: Previous week sleep summary
            current_recovery: Current week recovery summary
            previous_recovery: Previous week recovery summary

        Returns:
            WeeklyComparison with change percentages
        """
        def calc_change(current_val, previous_val):
            if previous_val == 0:
                return 100.0 if current_val > 0 else 0.0
            return round((current_val - previous_val) / previous_val * 100, 1)

        current_duration_hours = current.total_duration_seconds / 3600
        previous_duration_hours = previous.total_duration_seconds / 3600
        current_distance_km = current.total_distance_meters / 1000
        previous_distance_km = previous.total_distance_meters / 1000

        # Sleep score change (absolute difference)
        sleep_change = None
        if current_sleep.avg_sleep_score is not None and previous_sleep.avg_sleep_score is not None:
            sleep_change = round(current_sleep.avg_sleep_score - previous_sleep.avg_sleep_score, 1)

        # Recharge change (absolute difference)
        recharge_change = None
        if current_recovery.avg_recharge_status is not None and previous_recovery.avg_recharge_status is not None:
            recharge_change = round(current_recovery.avg_recharge_status - previous_recovery.avg_recharge_status, 2)

        return WeeklyComparison(
            current_sessions=current.total_sessions,
            previous_sessions=previous.total_sessions,
            session_change_percent=calc_change(current.total_sessions, previous.total_sessions),
            current_duration_hours=round(current_duration_hours, 1),
            previous_duration_hours=round(previous_duration_hours, 1),
            duration_change_percent=calc_change(current_duration_hours, previous_duration_hours),
            current_distance_km=round(current_distance_km, 1),
            previous_distance_km=round(previous_distance_km, 1),
            distance_change_percent=calc_change(current_distance_km, previous_distance_km),
            current_calories=current.total_calories,
            previous_calories=previous.total_calories,
            calories_change_percent=calc_change(current.total_calories, previous.total_calories),
            current_sleep_score=current_sleep.avg_sleep_score,
            previous_sleep_score=previous_sleep.avg_sleep_score,
            sleep_score_change=sleep_change,
            current_recharge=current_recovery.avg_recharge_status,
            previous_recharge=previous_recovery.avg_recharge_status,
            recharge_change=recharge_change
        )

    def generate_highlights(
        self,
        training: TrainingSummary,
        sleep: SleepSummary,
        recovery: RechargeSummary,
        comparison: Optional[WeeklyComparison]
    ) -> List[Highlight]:
        """
        Generate achievement highlights and concern warnings.

        Args:
            training: Training summary
            sleep: Sleep summary
            recovery: Recovery summary
            comparison: Week-over-week comparison

        Returns:
            List of Highlight objects
        """
        highlights = []

        # Training achievements
        if training.best_session:
            sport = training.best_session.sport or 'Session'
            duration_min = (training.best_session.duration_seconds or 0) // 60
            distance_km = (training.best_session.distance_meters or 0) / 1000

            if distance_km > 0:
                highlights.append(Highlight(
                    type='achievement',
                    icon='star',
                    message=f"Best session: {sport}",
                    details=f"{distance_km:.1f} km in {duration_min} minutes"
                ))
            else:
                highlights.append(Highlight(
                    type='achievement',
                    icon='star',
                    message=f"Best session: {sport}",
                    details=f"{duration_min} minutes"
                ))

        # Training load balance
        if training.total_cardio_load > 0 and training.total_muscle_load > 0:
            highlights.append(Highlight(
                type='achievement',
                icon='check',
                message="Training Load balanced",
                details=f"Cardio: {training.total_cardio_load:.0f}, Muscle: {training.total_muscle_load:.0f}"
            ))

        # Comparison-based achievements
        if comparison:
            if comparison.session_change_percent >= 25:
                highlights.append(Highlight(
                    type='achievement',
                    icon='trending-up',
                    message="Training volume up!",
                    details=f"+{comparison.session_change_percent:.0f}% more sessions than last week"
                ))

            if comparison.distance_change_percent >= 20:
                highlights.append(Highlight(
                    type='achievement',
                    icon='trending-up',
                    message="Distance increase",
                    details=f"+{comparison.distance_change_percent:.0f}% more distance covered"
                ))

            if comparison.sleep_score_change and comparison.sleep_score_change >= 5:
                highlights.append(Highlight(
                    type='achievement',
                    icon='moon',
                    message="Sleep quality improved!",
                    details=f"+{comparison.sleep_score_change:.0f} points from last week"
                ))

        # Sleep achievements
        if sleep.avg_sleep_score and sleep.avg_sleep_score >= 85:
            highlights.append(Highlight(
                type='achievement',
                icon='star',
                message="Excellent sleep quality",
                details=f"Average sleep score: {sleep.avg_sleep_score:.0f}/100"
            ))

        if sleep.avg_duration_hours >= 7.5:
            highlights.append(Highlight(
                type='achievement',
                icon='check',
                message="Great sleep duration",
                details=f"Averaging {sleep.avg_duration_hours:.1f} hours per night"
            ))

        # Recovery achievements
        if recovery.avg_recharge_status and recovery.avg_recharge_status >= 4:
            label = self.RECHARGE_STATUS.get(round(recovery.avg_recharge_status), 'Good')
            highlights.append(Highlight(
                type='achievement',
                icon='heart',
                message=f"Recovery status: {label}",
                details=f"Average: {recovery.avg_recharge_status:.1f}/5"
            ))

        # CONCERNS

        # Low recovery days
        if recovery.low_recharge_days:
            dates_str = ', '.join([d.strftime('%A') for d in recovery.low_recharge_days[:3]])
            highlights.append(Highlight(
                type='concern',
                icon='alert',
                message="Low recovery detected",
                details=f"Poor recharge on: {dates_str}"
            ))

        # Poor sleep
        if sleep.avg_sleep_score and sleep.avg_sleep_score < 70:
            highlights.append(Highlight(
                type='concern',
                icon='alert',
                message="Sleep quality needs attention",
                details=f"Average score: {sleep.avg_sleep_score:.0f}/100 - aim for 75+"
            ))

        if sleep.avg_duration_hours < 6.5 and sleep.total_nights > 0:
            highlights.append(Highlight(
                type='concern',
                icon='alert',
                message="Insufficient sleep duration",
                details=f"Only {sleep.avg_duration_hours:.1f} hours average - aim for 7-9 hours"
            ))

        # Training concerns
        if comparison:
            if comparison.duration_change_percent <= -30 and comparison.previous_duration_hours > 1:
                highlights.append(Highlight(
                    type='concern',
                    icon='trending-down',
                    message="Significant training decrease",
                    details=f"{comparison.duration_change_percent:.0f}% less training than last week"
                ))

        return highlights

    def determine_overall_rating(
        self,
        training: TrainingSummary,
        sleep: SleepSummary,
        recovery: RechargeSummary,
        highlights: List[Highlight]
    ) -> str:
        """
        Determine overall week rating based on all metrics.

        Returns:
            Rating string: 'Great Week!', 'Good Progress', 'Needs Attention', 'Take It Easy'
        """
        score = 0

        # Training contribution (0-30 points)
        if training.total_sessions >= 4:
            score += 20
        elif training.total_sessions >= 2:
            score += 10

        if training.total_duration_seconds >= 3 * 3600:  # 3+ hours
            score += 10

        # Sleep contribution (0-35 points)
        if sleep.avg_sleep_score:
            if sleep.avg_sleep_score >= 85:
                score += 25
            elif sleep.avg_sleep_score >= 75:
                score += 20
            elif sleep.avg_sleep_score >= 65:
                score += 10

        if sleep.avg_duration_hours >= 7:
            score += 10
        elif sleep.avg_duration_hours >= 6:
            score += 5

        # Recovery contribution (0-35 points)
        if recovery.avg_recharge_status:
            if recovery.avg_recharge_status >= 4:
                score += 25
            elif recovery.avg_recharge_status >= 3:
                score += 15
            elif recovery.avg_recharge_status >= 2:
                score += 5

        if len(recovery.low_recharge_days) == 0:
            score += 10
        elif len(recovery.low_recharge_days) <= 1:
            score += 5

        # Concerns penalty
        concerns = [h for h in highlights if h.type == 'concern']
        score -= len(concerns) * 5

        # Determine rating
        if score >= 75:
            return "Great Week!"
        elif score >= 50:
            return "Good Progress"
        elif score >= 30:
            return "Needs Attention"
        else:
            return "Take It Easy"

    def generate_report(self, week_start: date = None) -> WeeklyReport:
        """
        Generate complete weekly report.

        Args:
            week_start: Start of week (Monday). Defaults to last completed week.

        Returns:
            WeeklyReport with all aggregated data
        """
        session = get_session()

        try:
            # Determine week dates
            if week_start is None:
                current_start, current_end = self.get_week_dates()
            else:
                current_end = week_start + timedelta(days=6)
                current_start = week_start

            previous_start = current_start - timedelta(days=7)
            previous_end = current_end - timedelta(days=7)

            # Fetch data for current week
            current_exercises = get_exercises_in_range(
                session, self.user_id, current_start, current_end
            )
            current_sleep = get_sleep_in_range(
                session, self.user_id, current_start, current_end
            )
            current_recharge = get_recharge_in_range(
                session, self.user_id, current_start, current_end
            )

            # Fetch data for previous week
            previous_exercises = get_exercises_in_range(
                session, self.user_id, previous_start, previous_end
            )
            previous_sleep = get_sleep_in_range(
                session, self.user_id, previous_start, previous_end
            )
            previous_recharge = get_recharge_in_range(
                session, self.user_id, previous_start, previous_end
            )

            # Aggregate current week
            training_summary = self.aggregate_training(current_exercises)
            sleep_summary = self.aggregate_sleep(current_sleep)
            recovery_summary = self.aggregate_recovery(current_recharge)

            # Aggregate previous week
            prev_training = self.aggregate_training(previous_exercises)
            prev_sleep = self.aggregate_sleep(previous_sleep)
            prev_recovery = self.aggregate_recovery(previous_recharge)

            # Calculate comparison
            comparison = self.calculate_comparison(
                training_summary, prev_training,
                sleep_summary, prev_sleep,
                recovery_summary, prev_recovery
            )

            # Generate highlights
            highlights = self.generate_highlights(
                training_summary, sleep_summary, recovery_summary, comparison
            )

            # Determine overall rating
            rating = self.determine_overall_rating(
                training_summary, sleep_summary, recovery_summary, highlights
            )

            return WeeklyReport(
                week_start=current_start,
                week_end=current_end,
                training=training_summary,
                sleep=sleep_summary,
                recovery=recovery_summary,
                comparison=comparison,
                highlights=highlights,
                overall_rating=rating
            )

        finally:
            session.close()


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable string."""
    if seconds < 60:
        return f"{seconds}s"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}min"
    return f"{minutes}min"


def format_distance(meters: float) -> str:
    """Format distance in meters to km string."""
    km = meters / 1000
    if km >= 10:
        return f"{km:.1f} km"
    return f"{km:.2f} km"
