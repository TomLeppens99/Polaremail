"""
Weekly Health Digest - Advanced Training Analysis

This module provides sophisticated health and training metrics:
1. ACWR (Acute:Chronic Workload Ratio)
2. Training Monotony & Strain
3. HRV Trend Analysis (Mean + CV Quadrant)
4. Aerobic Decoupling Analysis
5. Sleep Architecture Analysis
6. Sleep Debt Tracker
7. Early Warning System (Illness/Overtraining Detection)
8. Weather-Performance Correlation
9. Time-of-Day Performance Optimization
10. Performance Management Chart (CTL/ATL/TSB)
"""

import math
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from .models import (
    get_session, Exercise, SleepRecord, NightlyRecharge, User,
    get_exercises_in_range, get_sleep_in_range, get_recharge_in_range
)
from .config import Config


# ============================================================================
# Data Classes for Feature Outputs
# ============================================================================

@dataclass
class ACWRResult:
    """Acute:Chronic Workload Ratio result."""
    acwr: float
    status: str  # "undertrained", "optimal", "caution", "danger"
    acute_load: float
    chronic_load: float
    trend: str  # "increasing", "decreasing", "stable"
    injury_risk_multiplier: float
    daily_loads_7_days: List[float] = field(default_factory=list)
    daily_loads_28_days: List[float] = field(default_factory=list)


@dataclass
class MonotonyStrainResult:
    """Training Monotony & Strain result."""
    monotony: float
    monotony_status: str  # "good", "elevated", "high_risk"
    strain: float
    weekly_total: float
    daily_mean: float
    daily_std: float
    interpretation: str


@dataclass
class HRVQuadrantResult:
    """HRV Trend Analysis result."""
    current_mean: float
    current_cv: float
    baseline_mean: float
    baseline_cv: float
    mean_deviation_percent: float
    cv_deviation: float
    quadrant: str  # "coping_well", "adapting", "fatigued", "maladaptation"
    interpretation: str
    trend_7_day: List[float] = field(default_factory=list)


@dataclass
class DecouplingResult:
    """Aerobic Decoupling Analysis result."""
    sessions_analyzed: int
    average_decoupling: float
    status: str  # "excellent", "good", "fair", "needs_work"
    interpretation: str
    trend_4_weeks: List[float] = field(default_factory=list)


@dataclass
class SleepArchitectureResult:
    """Sleep Architecture Analysis result."""
    avg_duration: str  # "7h 12m" format
    avg_duration_hours: float
    avg_efficiency: float
    composition: Dict[str, float]  # deep_percent, rem_percent, light_percent
    deficits: Dict[str, int]  # deep_deficit_nights, rem_deficit_nights
    nights_below_7h: int
    interpretation: str


@dataclass
class SleepDebtResult:
    """Sleep Debt Tracker result."""
    recent_debt_hours: float
    total_debt_hours: float
    status: str  # "none", "mild", "moderate", "severe"
    recovery_days_needed: float
    avg_vs_optimal: float
    trend: str  # "improving", "worsening"
    interpretation: str


@dataclass
class EarlyWarningResult:
    """Early Warning System result."""
    overall_status: str  # "clear", "attention_needed"
    risk_score: int  # 0-100
    warnings: List[Dict]
    recommendation: str


@dataclass
class WeatherPerformanceResult:
    """Weather-Performance Correlation result."""
    optimal_conditions: Dict[str, str]
    this_week_impact: Dict[str, float]
    performance_by_temp: Dict[str, float]
    upcoming_week_forecast: Optional[Dict] = None
    interpretation: str = ""


@dataclass
class TimeOfDayResult:
    """Time-of-Day Performance Optimization result."""
    optimal_slot: str
    optimal_time_range: str
    performance_by_slot: Dict[str, Dict]
    insight: str
    this_week_suggestion: str


@dataclass
class PerformanceManagementResult:
    """Performance Management Chart (CTL/ATL/TSB) result."""
    fitness_ctl: float
    fatigue_atl: float
    form_tsb: float
    form_status: str  # "detrained", "race_ready", "neutral", "tired", "very_fatigued"
    interpretation: str
    ctl_change_4_weeks: float
    peak_prediction: str
    series: Dict[str, List] = field(default_factory=dict)  # For charting


@dataclass
class HealthDigestReport:
    """Complete Health Digest report containing all features."""
    week_start: date
    week_end: date
    generation_time: datetime

    # Feature results
    acwr: Optional[ACWRResult] = None
    monotony_strain: Optional[MonotonyStrainResult] = None
    hrv_quadrant: Optional[HRVQuadrantResult] = None
    decoupling: Optional[DecouplingResult] = None
    sleep_architecture: Optional[SleepArchitectureResult] = None
    sleep_debt: Optional[SleepDebtResult] = None
    early_warning: Optional[EarlyWarningResult] = None
    weather_performance: Optional[WeatherPerformanceResult] = None
    time_of_day: Optional[TimeOfDayResult] = None
    performance_management: Optional[PerformanceManagementResult] = None

    # Insight of the week
    insight_of_week: str = ""


# ============================================================================
# Health Digest Calculator
# ============================================================================

class HealthDigestCalculator:
    """
    Calculator for all health digest metrics.
    Provides sophisticated analysis beyond basic metrics.
    """

    # Default optimal sleep hours
    DEFAULT_OPTIMAL_SLEEP_HOURS = 8.0

    # Time slots for time-of-day analysis
    TIME_SLOTS = {
        "early_morning": (5, 8),    # 5-8 AM
        "morning": (8, 11),          # 8-11 AM
        "midday": (11, 14),          # 11 AM - 2 PM
        "afternoon": (14, 17),       # 2-5 PM
        "evening": (17, 20),         # 5-8 PM
        "night": (20, 23)            # 8-11 PM
    }

    TIME_SLOT_LABELS = {
        "early_morning": "5-8 AM",
        "morning": "8-11 AM",
        "midday": "11 AM-2 PM",
        "afternoon": "2-5 PM",
        "evening": "5-8 PM",
        "night": "8-11 PM"
    }

    def __init__(self, user_id: str = None):
        """
        Initialize calculator.

        Args:
            user_id: Polar user ID (defaults to config)
        """
        self.user_id = user_id or Config.POLAR_USER_ID

    # =========================================================================
    # Feature 1: ACWR (Acute:Chronic Workload Ratio)
    # =========================================================================

    def calculate_trimp(
        self,
        duration_min: float,
        hr_avg: float,
        hr_rest: float,
        hr_max: float,
        gender: str = 'male'
    ) -> float:
        """
        Calculate TRIMP (Training Impulse) using Banister formula.

        Args:
            duration_min: Exercise duration in minutes
            hr_avg: Average heart rate during exercise
            hr_rest: Resting heart rate
            hr_max: Maximum heart rate
            gender: 'male' or 'female'

        Returns:
            TRIMP value
        """
        if hr_max <= hr_rest or duration_min <= 0:
            return 0.0

        b = 1.92 if gender == 'male' else 1.67
        hr_ratio = (hr_avg - hr_rest) / (hr_max - hr_rest)

        # Clamp hr_ratio to valid range
        hr_ratio = max(0.0, min(1.0, hr_ratio))

        try:
            return duration_min * hr_ratio * math.exp(b * hr_ratio)
        except (OverflowError, ValueError):
            return duration_min * hr_ratio

    def calculate_daily_training_load(
        self,
        exercises: List[Exercise],
        user: Optional[User] = None
    ) -> float:
        """
        Calculate daily training load from exercises.
        Uses Polar's training_load if available, otherwise calculates TRIMP.

        Args:
            exercises: List of exercises for the day
            user: Optional User object for TRIMP calculation

        Returns:
            Daily training load value
        """
        total_load = 0.0

        for ex in exercises:
            # Prefer Polar's training load if available
            if ex.training_load_cardio:
                total_load += ex.training_load_cardio
            elif ex.average_heart_rate and ex.duration_seconds:
                # Calculate TRIMP as fallback
                duration_min = ex.duration_seconds / 60
                hr_avg = ex.average_heart_rate
                hr_max = ex.max_heart_rate or 190
                hr_rest = 60  # Default resting HR

                gender = 'male'
                if user and user.gender:
                    gender = user.gender.lower()

                trimp = self.calculate_trimp(
                    duration_min, hr_avg, hr_rest, hr_max, gender
                )
                total_load += trimp

        return total_load

    def calculate_ewma(self, loads: List[float], days: int) -> float:
        """
        Calculate Exponentially Weighted Moving Average.

        Args:
            loads: List of daily loads (oldest to newest)
            days: Number of days for the EWMA period

        Returns:
            EWMA value
        """
        if not loads:
            return 0.0

        lambda_val = 2 / (days + 1)
        ewma = loads[0]

        for load in loads[1:]:
            ewma = load * lambda_val + (1 - lambda_val) * ewma

        return ewma

    def calculate_ewma_series(self, loads: List[float], days: int) -> List[float]:
        """
        Calculate EWMA series for charting.

        Args:
            loads: List of daily loads
            days: Number of days for the EWMA period

        Returns:
            List of EWMA values
        """
        if not loads:
            return []

        lambda_val = 2 / (days + 1)
        result = [loads[0]]

        for i in range(1, len(loads)):
            result.append(loads[i] * lambda_val + (1 - lambda_val) * result[-1])

        return result

    def calculate_acwr(
        self,
        exercises_28_days: List[Exercise],
        user: Optional[User] = None
    ) -> Optional[ACWRResult]:
        """
        Calculate Acute:Chronic Workload Ratio.

        Args:
            exercises_28_days: Exercises from the last 28 days
            user: Optional User for TRIMP calculation

        Returns:
            ACWRResult or None if insufficient data
        """
        if not exercises_28_days:
            return None

        # Group exercises by date
        exercises_by_date = defaultdict(list)
        today = date.today()

        for ex in exercises_28_days:
            if ex.start_time:
                ex_date = ex.start_time.date()
                exercises_by_date[ex_date].append(ex)

        # Calculate daily loads for last 28 days
        daily_loads_28 = []
        for i in range(28, 0, -1):
            day = today - timedelta(days=i)
            day_exercises = exercises_by_date.get(day, [])
            daily_load = self.calculate_daily_training_load(day_exercises, user)
            daily_loads_28.append(daily_load)

        # Last 7 days
        daily_loads_7 = daily_loads_28[-7:]

        # Calculate ACWR using EWMA
        acute_load = self.calculate_ewma(daily_loads_7, 7)
        chronic_load = self.calculate_ewma(daily_loads_28, 28)

        if chronic_load > 0:
            acwr = acute_load / chronic_load
        else:
            acwr = 0.0

        # Determine status
        if acwr < 0.8:
            status = "undertrained"
            injury_risk = 1.0
        elif acwr <= 1.3:
            status = "optimal"
            injury_risk = 1.0
        elif acwr <= 1.5:
            status = "caution"
            injury_risk = 2.0
        else:
            status = "danger"
            injury_risk = 4.0

        # Calculate trend (compare to last week)
        if len(daily_loads_28) >= 14:
            last_week_acute = self.calculate_ewma(daily_loads_28[-14:-7], 7)
            if last_week_acute > 0:
                if acute_load > last_week_acute * 1.05:
                    trend = "increasing"
                elif acute_load < last_week_acute * 0.95:
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return ACWRResult(
            acwr=round(acwr, 2),
            status=status,
            acute_load=round(acute_load, 1),
            chronic_load=round(chronic_load, 1),
            trend=trend,
            injury_risk_multiplier=injury_risk,
            daily_loads_7_days=daily_loads_7,
            daily_loads_28_days=daily_loads_28
        )

    # =========================================================================
    # Feature 2: Training Monotony & Strain
    # =========================================================================

    def calculate_monotony_strain(
        self,
        daily_loads_7_days: List[float]
    ) -> Optional[MonotonyStrainResult]:
        """
        Calculate Training Monotony and Strain.

        Monotony = mean / std_dev (lower is better, <1.5 ideal)
        Strain = weekly_total * monotony (composite risk score)

        Args:
            daily_loads_7_days: List of daily training loads for 7 days

        Returns:
            MonotonyStrainResult or None if insufficient data
        """
        if not daily_loads_7_days or len(daily_loads_7_days) < 2:
            return None

        weekly_total = sum(daily_loads_7_days)
        mean_load = statistics.mean(daily_loads_7_days)

        try:
            std_dev = statistics.stdev(daily_loads_7_days)
        except statistics.StatisticsError:
            std_dev = 0

        # Calculate monotony (mean / std_dev)
        # When std_dev is 0 with positive load, this represents extreme monotony
        MAX_MONOTONY = 99.99  # Cap to avoid infinity issues
        if std_dev > 0:
            monotony = mean_load / std_dev
        else:
            monotony = MAX_MONOTONY if mean_load > 0 else 0

        # Calculate strain (high strain with high monotony indicates risk)
        strain = weekly_total * monotony

        # Determine status
        if monotony < 1.5:
            status = "good"
            interpretation = "Good training variation this week"
        elif monotony < 2.0:
            status = "elevated"
            interpretation = "Training could use more variation"
        else:
            status = "high_risk"
            interpretation = "High illness/injury risk - add more variety"

        return MonotonyStrainResult(
            monotony=round(monotony, 2) if monotony < MAX_MONOTONY else MAX_MONOTONY,
            monotony_status=status,
            strain=round(strain, 0),
            weekly_total=round(weekly_total, 1),
            daily_mean=round(mean_load, 1),
            daily_std=round(std_dev, 1),
            interpretation=interpretation
        )

    # =========================================================================
    # Feature 3: HRV Trend Analysis
    # =========================================================================

    def analyze_hrv_trends(
        self,
        hrv_values_7_days: List[float],
        hrv_baseline_60_days: List[float]
    ) -> Optional[HRVQuadrantResult]:
        """
        Analyze HRV trends using quadrant analysis.

        Quadrants:
        - High HRV + Low CV = Coping Well (optimal)
        - High HRV + High CV = Adapting (responding to training)
        - Low HRV + High CV = Fatigued (needs recovery)
        - Low HRV + Low CV = Maladaptation (chronic stress/overtraining)

        Args:
            hrv_values_7_days: HRV values from last 7 days
            hrv_baseline_60_days: HRV values from last 60 days (baseline)

        Returns:
            HRVQuadrantResult or None if insufficient data
        """
        if not hrv_values_7_days or len(hrv_values_7_days) < 3:
            return None
        if not hrv_baseline_60_days or len(hrv_baseline_60_days) < 14:
            return None

        # Current week stats
        current_mean = statistics.mean(hrv_values_7_days)
        current_std = statistics.stdev(hrv_values_7_days) if len(hrv_values_7_days) > 1 else 0
        current_cv = (current_std / current_mean) * 100 if current_mean > 0 else 0

        # Baseline stats (60-day)
        baseline_mean = statistics.mean(hrv_baseline_60_days)
        baseline_std = statistics.stdev(hrv_baseline_60_days) if len(hrv_baseline_60_days) > 1 else 0
        baseline_cv = (baseline_std / baseline_mean) * 100 if baseline_mean > 0 else 0

        # Deviations from baseline
        mean_deviation = ((current_mean - baseline_mean) / baseline_mean * 100
                          if baseline_mean > 0 else 0)
        cv_deviation = current_cv - baseline_cv

        # Quadrant classification
        high_hrv = mean_deviation > -5  # within 5% of baseline or higher
        low_cv = cv_deviation < 5  # CV not elevated more than 5 points

        if high_hrv and low_cv:
            quadrant = "coping_well"
            interpretation = "Recovery status good. Body is handling current training load well."
        elif high_hrv and not low_cv:
            quadrant = "adapting"
            interpretation = "Body is responding to training stimulus. Monitor for fatigue."
        elif not high_hrv and not low_cv:
            quadrant = "fatigued"
            interpretation = "Signs of fatigue. Consider reducing training intensity."
        else:
            quadrant = "maladaptation"
            interpretation = "Warning: Signs of chronic stress. Prioritize recovery."

        return HRVQuadrantResult(
            current_mean=round(current_mean, 1),
            current_cv=round(current_cv, 1),
            baseline_mean=round(baseline_mean, 1),
            baseline_cv=round(baseline_cv, 1),
            mean_deviation_percent=round(mean_deviation, 1),
            cv_deviation=round(cv_deviation, 1),
            quadrant=quadrant,
            interpretation=interpretation,
            trend_7_day=hrv_values_7_days
        )

    # =========================================================================
    # Feature 4: Aerobic Decoupling Analysis
    # =========================================================================

    def calculate_decoupling_for_exercise(self, exercise: Exercise) -> Optional[float]:
        """
        Calculate aerobic decoupling for a single exercise.

        Decoupling% = ((ratio_1st - ratio_2nd) / ratio_1st) * 100

        Args:
            exercise: Exercise record with HR and pace data

        Returns:
            Decoupling percentage or None if insufficient data
        """
        # Need at least 45 minutes and HR data
        if not exercise.duration_seconds or exercise.duration_seconds < 45 * 60:
            return None
        if not exercise.average_heart_rate:
            return None
        if not exercise.distance_meters or exercise.distance_meters <= 0:
            return None

        # For now, use overall metrics since we don't have detailed samples
        # This is a simplified calculation
        # In a full implementation, we would analyze HR and pace samples

        # Calculate overall efficiency (pace/HR ratio)
        pace_min_km = (exercise.duration_seconds / 60) / (exercise.distance_meters / 1000)
        overall_efficiency = pace_min_km / exercise.average_heart_rate

        # Without sample data, we can't calculate true decoupling
        # Return None to indicate insufficient data for this analysis
        return None

    def analyze_decoupling(
        self,
        exercises: List[Exercise],
        weeks: int = 4
    ) -> Optional[DecouplingResult]:
        """
        Analyze aerobic decoupling over multiple weeks.

        Args:
            exercises: List of exercises
            weeks: Number of weeks to analyze

        Returns:
            DecouplingResult or None if insufficient data
        """
        # Filter for endurance sessions (45+ minutes)
        endurance_sessions = [
            ex for ex in exercises
            if ex.duration_seconds and ex.duration_seconds >= 45 * 60
            and ex.distance_meters and ex.distance_meters > 0
            and ex.average_heart_rate
        ]

        if not endurance_sessions:
            return DecouplingResult(
                sessions_analyzed=0,
                average_decoupling=0.0,
                status="insufficient_data",
                interpretation="Not enough endurance sessions for analysis",
                trend_4_weeks=[]
            )

        # Without detailed sample data, provide a simplified analysis
        # based on pace efficiency (pace per HR beat)
        sessions_analyzed = len(endurance_sessions)

        # Calculate average efficiency
        efficiencies = []
        for ex in endurance_sessions:
            pace_min_km = (ex.duration_seconds / 60) / (ex.distance_meters / 1000)
            efficiency = pace_min_km / ex.average_heart_rate
            efficiencies.append(efficiency)

        avg_efficiency = statistics.mean(efficiencies) if efficiencies else 0

        # Since we don't have sample data, use a placeholder message
        return DecouplingResult(
            sessions_analyzed=sessions_analyzed,
            average_decoupling=0.0,
            status="needs_sample_data",
            interpretation=f"Analyzed {sessions_analyzed} endurance sessions. "
                           "Detailed decoupling requires HR/pace samples.",
            trend_4_weeks=[]
        )

    # =========================================================================
    # Feature 5: Sleep Architecture Analysis
    # =========================================================================

    def analyze_sleep_architecture(
        self,
        sleep_records: List[SleepRecord]
    ) -> Optional[SleepArchitectureResult]:
        """
        Analyze sleep architecture (deep/REM/light percentages).

        Healthy targets:
        - Light (N1+N2): 45-55%
        - Deep (N3): 15-25%
        - REM: 20-25%
        - Efficiency: >85%

        Args:
            sleep_records: List of sleep records

        Returns:
            SleepArchitectureResult or None if insufficient data
        """
        if not sleep_records:
            return None

        total_nights = len(sleep_records)
        nights_below_7h = 0
        deep_deficit_nights = 0
        rem_deficit_nights = 0

        durations = []
        deep_percents = []
        rem_percents = []
        light_percents = []

        for record in sleep_records:
            if not record.duration_seconds:
                continue

            total_min = record.duration_seconds / 60
            durations.append(total_min)

            if total_min < 420:  # 7 hours
                nights_below_7h += 1

            # Calculate percentages
            deep_min = (record.deep_sleep_seconds or 0) / 60
            rem_min = (record.rem_sleep_seconds or 0) / 60
            light_min = (record.light_sleep_seconds or 0) / 60

            if total_min > 0:
                deep_pct = (deep_min / total_min) * 100
                rem_pct = (rem_min / total_min) * 100
                light_pct = (light_min / total_min) * 100

                deep_percents.append(deep_pct)
                rem_percents.append(rem_pct)
                light_percents.append(light_pct)

                if deep_pct < 15:
                    deep_deficit_nights += 1
                if rem_pct < 20:
                    rem_deficit_nights += 1

        if not durations:
            return None

        avg_duration_min = statistics.mean(durations)
        avg_duration_hours = avg_duration_min / 60
        hours = int(avg_duration_hours)
        mins = int((avg_duration_hours - hours) * 60)

        avg_deep = statistics.mean(deep_percents) if deep_percents else 0
        avg_rem = statistics.mean(rem_percents) if rem_percents else 0
        avg_light = statistics.mean(light_percents) if light_percents else 0

        # Determine deep/REM status
        deep_status = "good" if 15 <= avg_deep <= 25 else ("low" if avg_deep < 15 else "high")
        rem_status = "good" if 20 <= avg_rem <= 25 else ("low" if avg_rem < 20 else "high")

        # Build interpretation
        issues = []
        if deep_deficit_nights > 0:
            issues.append(f"Deep sleep below target on {deep_deficit_nights} night(s)")
        if rem_deficit_nights > 0:
            issues.append(f"REM sleep below target on {rem_deficit_nights} night(s)")
        if nights_below_7h > 2:
            issues.append(f"Slept less than 7 hours on {nights_below_7h} nights")

        if not issues:
            interpretation = "Sleep architecture is healthy."
        else:
            interpretation = "; ".join(issues)

        return SleepArchitectureResult(
            avg_duration=f"{hours}h {mins}m",
            avg_duration_hours=round(avg_duration_hours, 2),
            avg_efficiency=85.0,  # Placeholder - would need time in bed data
            composition={
                "deep_percent": round(avg_deep, 1),
                "deep_status": deep_status,
                "rem_percent": round(avg_rem, 1),
                "rem_status": rem_status,
                "light_percent": round(avg_light, 1)
            },
            deficits={
                "deep_deficit_nights": deep_deficit_nights,
                "rem_deficit_nights": rem_deficit_nights
            },
            nights_below_7h=nights_below_7h,
            interpretation=interpretation
        )

    # =========================================================================
    # Feature 6: Sleep Debt Tracker
    # =========================================================================

    def calculate_sleep_debt(
        self,
        sleep_records: List[SleepRecord],
        optimal_hours: float = None
    ) -> Optional[SleepDebtResult]:
        """
        Calculate accumulated sleep deficit.

        Args:
            sleep_records: List of sleep records (14+ days preferred)
            optimal_hours: User's optimal sleep need (default 8.0h)

        Returns:
            SleepDebtResult or None if insufficient data
        """
        if not sleep_records:
            return None

        if optimal_hours is None:
            optimal_hours = self.DEFAULT_OPTIMAL_SLEEP_HOURS

        optimal_min = optimal_hours * 60

        # Get durations in minutes
        durations = []
        for record in sleep_records:
            if record.duration_seconds:
                durations.append(record.duration_seconds / 60)

        if not durations:
            return None

        # Calculate daily deltas
        daily_deltas = [d - optimal_min for d in durations]

        # Recent debt (last 7 days)
        recent_durations = durations[-7:] if len(durations) >= 7 else durations
        recent_deltas = [d - optimal_min for d in recent_durations]
        recent_debt_min = -sum(d for d in recent_deltas if d < 0)

        # Total debt (all available days)
        total_debt_min = -sum(d for d in daily_deltas if d < 0)

        # Recovery estimate (4 days per hour to recover)
        debt_hours = recent_debt_min / 60
        recovery_days = debt_hours * 4

        # Determine status
        if debt_hours <= 0:
            status = "none"
        elif debt_hours < 3:
            status = "mild"
        elif debt_hours <= 7:
            status = "moderate"
        else:
            status = "severe"

        # Calculate trend
        if len(durations) >= 7:
            if durations[-1] > durations[-7]:
                trend = "improving"
            else:
                trend = "worsening"
        else:
            trend = "stable"

        # Average vs optimal
        avg_duration = statistics.mean(durations) / 60
        avg_vs_optimal = avg_duration - optimal_hours

        # Interpretation
        if status == "none":
            interpretation = "No sleep debt. Great job!"
        elif status == "mild":
            interpretation = f"Mild sleep deficit of {debt_hours:.1f} hours."
        elif status == "moderate":
            interpretation = (f"Running a {debt_hours:.1f} hour sleep deficit. "
                              f"Need ~{int(recovery_days)} days of optimal sleep to recover.")
        else:
            interpretation = (f"Severe sleep debt of {debt_hours:.1f} hours. "
                              "Prioritize sleep for recovery.")

        return SleepDebtResult(
            recent_debt_hours=round(debt_hours, 1),
            total_debt_hours=round(total_debt_min / 60, 1),
            status=status,
            recovery_days_needed=round(recovery_days, 0),
            avg_vs_optimal=round(avg_vs_optimal, 1),
            trend=trend,
            interpretation=interpretation
        )

    # =========================================================================
    # Feature 7: Early Warning System
    # =========================================================================

    def check_early_warnings(
        self,
        recharge_records_recent: List[NightlyRecharge],
        recharge_records_baseline: List[NightlyRecharge]
    ) -> EarlyWarningResult:
        """
        Check for early signs of illness or overtraining.

        Red flags:
        - Resting HR: >5 bpm above baseline for 2+ days
        - HRV: >1 SD below baseline for 2+ days

        Args:
            recharge_records_recent: Last 3-7 days of recharge data
            recharge_records_baseline: 30+ days of baseline data

        Returns:
            EarlyWarningResult
        """
        warnings = []

        # Need baseline data
        if not recharge_records_baseline or len(recharge_records_baseline) < 14:
            return EarlyWarningResult(
                overall_status="insufficient_data",
                risk_score=0,
                warnings=[],
                recommendation="Need more historical data for early warning detection"
            )

        # Calculate baselines
        baseline_hrs = [r.heart_rate_avg for r in recharge_records_baseline
                        if r.heart_rate_avg is not None]
        baseline_hrvs = [r.hrv_avg for r in recharge_records_baseline
                         if r.hrv_avg is not None]

        if not baseline_hrs or not baseline_hrvs:
            return EarlyWarningResult(
                overall_status="insufficient_data",
                risk_score=0,
                warnings=[],
                recommendation="Need more HR/HRV data for early warning detection"
            )

        hr_baseline_mean = statistics.mean(baseline_hrs)
        hrv_baseline_mean = statistics.mean(baseline_hrvs)
        hrv_baseline_std = statistics.stdev(baseline_hrvs) if len(baseline_hrvs) > 1 else 0

        # Check recent data
        if recharge_records_recent:
            recent_hrs = [r.heart_rate_avg for r in recharge_records_recent
                          if r.heart_rate_avg is not None]
            recent_hrvs = [r.hrv_avg for r in recharge_records_recent
                           if r.hrv_avg is not None]

            # Resting HR check
            if recent_hrs:
                recent_hr_mean = statistics.mean(recent_hrs[-3:] if len(recent_hrs) >= 3 else recent_hrs)
                hr_elevation = recent_hr_mean - hr_baseline_mean

                if hr_elevation > 5:
                    warnings.append({
                        "type": "elevated_rhr",
                        "severity": "warning",
                        "value": round(recent_hr_mean, 0),
                        "baseline": round(hr_baseline_mean, 0),
                        "message": f"Resting HR elevated {hr_elevation:.0f} bpm above baseline"
                    })

            # HRV suppression check
            if recent_hrvs:
                recent_hrv_mean = statistics.mean(recent_hrvs[-3:] if len(recent_hrvs) >= 3 else recent_hrvs)

                if recent_hrv_mean < hrv_baseline_mean - hrv_baseline_std:
                    warnings.append({
                        "type": "suppressed_hrv",
                        "severity": "warning",
                        "value": round(recent_hrv_mean, 1),
                        "baseline": round(hrv_baseline_mean, 1),
                        "message": "HRV suppressed >1 SD below baseline"
                    })

        # Calculate risk score
        risk_score = min(len(warnings) * 25, 100)

        # Determine overall status
        if warnings:
            overall_status = "attention_needed"
            recommendation = "Consider reducing training intensity. Monitor for illness symptoms."
        else:
            overall_status = "clear"
            recommendation = "All vitals within normal range."

        return EarlyWarningResult(
            overall_status=overall_status,
            risk_score=risk_score,
            warnings=warnings,
            recommendation=recommendation
        )

    # =========================================================================
    # Feature 8: Weather-Performance Correlation
    # =========================================================================

    def analyze_weather_performance(
        self,
        exercises_with_weather: List[Dict]
    ) -> Optional[WeatherPerformanceResult]:
        """
        Analyze weather impact on performance.

        Note: Requires weather data to be fetched separately.

        Args:
            exercises_with_weather: List of exercises with weather data attached

        Returns:
            WeatherPerformanceResult or None if insufficient data
        """
        if not exercises_with_weather or len(exercises_with_weather) < 10:
            return WeatherPerformanceResult(
                optimal_conditions={"temperature": "Unknown"},
                this_week_impact={"avg_temp": 0, "estimated_impact": 0},
                performance_by_temp={},
                interpretation="Need more data with weather info for analysis"
            )

        # Group by temperature bands
        temp_bands = {
            "cold": [],      # <10°C
            "cool": [],      # 10-15°C
            "moderate": [],  # 15-20°C
            "warm": [],      # 20-25°C
            "hot": []        # >25°C
        }

        for ex_data in exercises_with_weather:
            ex = ex_data.get("exercise")
            weather = ex_data.get("weather")

            if not weather or not ex:
                continue

            temp = weather.get("temp_c", 15)

            # Calculate efficiency (lower pace per HR is better)
            if ex.distance_meters and ex.duration_seconds and ex.average_heart_rate:
                pace = (ex.duration_seconds / 60) / (ex.distance_meters / 1000)
                efficiency = pace / ex.average_heart_rate

                if temp < 10:
                    temp_bands["cold"].append(efficiency)
                elif temp < 15:
                    temp_bands["cool"].append(efficiency)
                elif temp < 20:
                    temp_bands["moderate"].append(efficiency)
                elif temp < 25:
                    temp_bands["warm"].append(efficiency)
                else:
                    temp_bands["hot"].append(efficiency)

        # Calculate averages
        band_averages = {}
        for band, values in temp_bands.items():
            if len(values) >= 3:
                band_averages[band] = statistics.mean(values)

        if not band_averages:
            return WeatherPerformanceResult(
                optimal_conditions={"temperature": "Unknown"},
                this_week_impact={"avg_temp": 0, "estimated_impact": 0},
                performance_by_temp={},
                interpretation="Need more sessions in varied conditions"
            )

        # Find optimal (lowest efficiency ratio = best performance)
        optimal_band = min(band_averages, key=band_averages.get)

        temp_ranges = {
            "cold": "<10°C",
            "cool": "10-15°C",
            "moderate": "15-20°C",
            "warm": "20-25°C",
            "hot": ">25°C"
        }

        return WeatherPerformanceResult(
            optimal_conditions={
                "temperature": temp_ranges.get(optimal_band, "Unknown"),
                "band": optimal_band
            },
            this_week_impact={"avg_temp": 0, "estimated_impact": 0},
            performance_by_temp=band_averages,
            interpretation=f"Best performance in {temp_ranges.get(optimal_band, 'moderate')} conditions"
        )

    # =========================================================================
    # Feature 9: Time-of-Day Performance Optimization
    # =========================================================================

    def analyze_time_of_day_performance(
        self,
        exercises: List[Exercise]
    ) -> Optional[TimeOfDayResult]:
        """
        Identify personal peak performance windows.

        Args:
            exercises: List of exercises (20-30+ for meaningful patterns)

        Returns:
            TimeOfDayResult or None if insufficient data
        """
        if not exercises or len(exercises) < 10:
            return None

        # Group exercises by time slot
        slot_data = {slot: [] for slot in self.TIME_SLOTS}

        for ex in exercises:
            if not ex.start_time:
                continue

            hour = ex.start_time.hour

            for slot_name, (start_hour, end_hour) in self.TIME_SLOTS.items():
                if start_hour <= hour < end_hour:
                    # Calculate normalized performance
                    if ex.distance_meters and ex.duration_seconds and ex.average_heart_rate:
                        pace = (ex.duration_seconds / 60) / (ex.distance_meters / 1000)
                        efficiency = pace / ex.average_heart_rate
                        slot_data[slot_name].append(efficiency)
                    break

        # Calculate stats per slot
        results = {}
        for slot_name, efficiencies in slot_data.items():
            if len(efficiencies) >= 3:
                results[slot_name] = {
                    "avg_efficiency": statistics.mean(efficiencies),
                    "sample_size": len(efficiencies)
                }

        if not results:
            return TimeOfDayResult(
                optimal_slot="unknown",
                optimal_time_range="Unknown",
                performance_by_slot={},
                insight="Need more varied training times for analysis",
                this_week_suggestion="Try training at different times"
            )

        # Find optimal (lowest efficiency = best performance)
        optimal_slot = min(results, key=lambda x: results[x]["avg_efficiency"])

        # Calculate relative performance
        optimal_eff = results[optimal_slot]["avg_efficiency"]
        performance_by_slot = {}

        for slot, data in results.items():
            if optimal_eff > 0:
                relative_perf = ((data["avg_efficiency"] - optimal_eff) / optimal_eff) * 100
            else:
                relative_perf = 0
            performance_by_slot[slot] = {
                "relative_performance": round(relative_perf, 1),
                "sample_size": data["sample_size"]
            }

        # Generate insight
        if performance_by_slot:
            worst_slot = max(performance_by_slot,
                             key=lambda x: performance_by_slot[x]["relative_performance"])
            diff = abs(performance_by_slot.get(worst_slot, {}).get("relative_performance", 0))
            insight = (f"You perform {diff:.1f}% better in {optimal_slot.replace('_', ' ')}s "
                       f"vs {worst_slot.replace('_', ' ')}s")
        else:
            insight = "Need more data for performance insights"

        return TimeOfDayResult(
            optimal_slot=optimal_slot,
            optimal_time_range=self.TIME_SLOT_LABELS.get(optimal_slot, "Unknown"),
            performance_by_slot=performance_by_slot,
            insight=insight,
            this_week_suggestion=f"Schedule key workouts in the {optimal_slot.replace('_', ' ')} when possible"
        )

    # =========================================================================
    # Feature 10: Performance Management Chart (CTL/ATL/TSB)
    # =========================================================================

    def calculate_performance_management(
        self,
        daily_loads: List[float]
    ) -> Optional[PerformanceManagementResult]:
        """
        Calculate CTL/ATL/TSB for Performance Management Chart.

        CTL (Chronic Training Load) = 42-day EWMA = "Fitness"
        ATL (Acute Training Load) = 7-day EWMA = "Fatigue"
        TSB (Training Stress Balance) = CTL - ATL = "Form"

        Args:
            daily_loads: Daily training loads (42+ days preferred)

        Returns:
            PerformanceManagementResult or None if insufficient data
        """
        if not daily_loads or len(daily_loads) < 14:
            return None

        # Pad to 42 days if needed
        if len(daily_loads) < 42:
            padding = [0.0] * (42 - len(daily_loads))
            daily_loads = padding + daily_loads

        # Calculate series
        ctl_series = self.calculate_ewma_series(daily_loads, 42)
        atl_series = self.calculate_ewma_series(daily_loads, 7)
        tsb_series = [ctl - atl for ctl, atl in zip(ctl_series, atl_series)]

        current_ctl = ctl_series[-1]
        current_atl = atl_series[-1]
        current_tsb = tsb_series[-1]

        # Determine form status
        if current_tsb > 25:
            form_status = "detrained"
        elif current_tsb >= 10:
            form_status = "race_ready"
        elif current_tsb >= 0:
            form_status = "neutral"
        elif current_tsb >= -10:
            form_status = "tired"
        else:
            form_status = "very_fatigued"

        # Calculate CTL change over 4 weeks
        if len(ctl_series) >= 28:
            ctl_4_weeks_ago = ctl_series[-28]
            ctl_change = current_ctl - ctl_4_weeks_ago
        else:
            ctl_change = 0

        # Generate interpretation
        if form_status == "race_ready":
            interpretation = "Excellent form! Good time for key workouts or races."
            peak_prediction = "You are ready to perform now"
        elif form_status == "tired":
            interpretation = "Fitness is building but carrying fatigue. Good training block."
            peak_prediction = "With a taper, you could peak in 10-14 days"
        elif form_status == "very_fatigued":
            interpretation = "High fatigue - consider a recovery period."
            peak_prediction = "With a taper, you could peak in 14-21 days"
        elif form_status == "neutral":
            interpretation = "Balanced state - can train or race effectively."
            peak_prediction = "Ready for moderate efforts"
        else:
            interpretation = "Low fitness/fatigue - consider building training load."
            peak_prediction = "Build fitness before targeting a peak"

        return PerformanceManagementResult(
            fitness_ctl=round(current_ctl, 1),
            fatigue_atl=round(current_atl, 1),
            form_tsb=round(current_tsb, 1),
            form_status=form_status,
            interpretation=interpretation,
            ctl_change_4_weeks=round(ctl_change, 1),
            peak_prediction=peak_prediction,
            series={
                "ctl": [round(x, 1) for x in ctl_series],
                "atl": [round(x, 1) for x in atl_series],
                "tsb": [round(x, 1) for x in tsb_series]
            }
        )

    # =========================================================================
    # Main Report Generation
    # =========================================================================

    def generate_health_digest(
        self,
        week_start: date = None
    ) -> HealthDigestReport:
        """
        Generate complete Health Digest report.

        Args:
            week_start: Start of week (Monday). Defaults to last completed week.

        Returns:
            HealthDigestReport with all analysis results
        """
        session = get_session()

        try:
            # Determine week dates
            if week_start is None:
                today = date.today()
                days_since_monday = today.weekday()
                current_week_monday = today - timedelta(days=days_since_monday)
                week_start = current_week_monday - timedelta(days=7)

            week_end = week_start + timedelta(days=6)

            # Fetch data for various time ranges
            # Current week
            exercises_week = get_exercises_in_range(
                session, self.user_id, week_start, week_end
            )

            # Last 28 days for ACWR
            start_28 = week_end - timedelta(days=27)
            exercises_28 = get_exercises_in_range(
                session, self.user_id, start_28, week_end
            )

            # Last 42 days for CTL
            start_42 = week_end - timedelta(days=41)
            exercises_42 = get_exercises_in_range(
                session, self.user_id, start_42, week_end
            )

            # Last 60 days for HRV baseline
            start_60 = week_end - timedelta(days=59)
            recharge_60 = get_recharge_in_range(
                session, self.user_id, start_60, week_end
            )

            # Current week recharge
            recharge_week = get_recharge_in_range(
                session, self.user_id, week_start, week_end
            )

            # Sleep data (14 days)
            start_14 = week_end - timedelta(days=13)
            sleep_14 = get_sleep_in_range(
                session, self.user_id, start_14, week_end
            )

            # Sleep data (7 days)
            sleep_week = get_sleep_in_range(
                session, self.user_id, week_start, week_end
            )

            # Get user for TRIMP calculation
            from .models import User
            user = session.query(User).filter_by(polar_user_id=self.user_id).first()

            # ===== Calculate Features =====

            # Feature 1: ACWR
            acwr_result = self.calculate_acwr(exercises_28, user)

            # Feature 2: Monotony & Strain
            monotony_result = None
            if acwr_result and acwr_result.daily_loads_7_days:
                monotony_result = self.calculate_monotony_strain(acwr_result.daily_loads_7_days)

            # Feature 3: HRV Quadrant
            hrv_week = [r.hrv_avg for r in recharge_week if r.hrv_avg]
            hrv_baseline = [r.hrv_avg for r in recharge_60 if r.hrv_avg]
            hrv_result = self.analyze_hrv_trends(hrv_week, hrv_baseline)

            # Feature 4: Decoupling
            decoupling_result = self.analyze_decoupling(exercises_28)

            # Feature 5: Sleep Architecture
            sleep_arch_result = self.analyze_sleep_architecture(sleep_week)

            # Feature 6: Sleep Debt
            sleep_debt_result = self.calculate_sleep_debt(sleep_14)

            # Feature 7: Early Warnings
            early_warning_result = self.check_early_warnings(
                recharge_week, recharge_60
            )

            # Feature 8: Weather (requires external API - placeholder)
            weather_result = WeatherPerformanceResult(
                optimal_conditions={"temperature": "Not available"},
                this_week_impact={},
                performance_by_temp={},
                interpretation="Weather data requires OpenWeatherMap API integration"
            )

            # Feature 9: Time of Day
            time_of_day_result = self.analyze_time_of_day_performance(exercises_42)

            # Feature 10: Performance Management
            pm_result = None
            if acwr_result and acwr_result.daily_loads_28_days:
                # Extend to 42 days
                daily_loads_42 = []
                exercises_by_date = defaultdict(list)
                for ex in exercises_42:
                    if ex.start_time:
                        exercises_by_date[ex.start_time.date()].append(ex)

                for i in range(42, 0, -1):
                    day = week_end - timedelta(days=i-1)
                    day_exercises = exercises_by_date.get(day, [])
                    daily_load = self.calculate_daily_training_load(day_exercises, user)
                    daily_loads_42.append(daily_load)

                pm_result = self.calculate_performance_management(daily_loads_42)

            # Generate insight of the week
            insights = []
            if time_of_day_result and time_of_day_result.insight:
                insights.append(time_of_day_result.insight)
            if hrv_result:
                insights.append(hrv_result.interpretation)
            if acwr_result and acwr_result.status == "optimal":
                insights.append("Training load is in the optimal zone")

            insight_of_week = insights[0] if insights else "Keep training consistently!"

            return HealthDigestReport(
                week_start=week_start,
                week_end=week_end,
                generation_time=datetime.now(),
                acwr=acwr_result,
                monotony_strain=monotony_result,
                hrv_quadrant=hrv_result,
                decoupling=decoupling_result,
                sleep_architecture=sleep_arch_result,
                sleep_debt=sleep_debt_result,
                early_warning=early_warning_result,
                weather_performance=weather_result,
                time_of_day=time_of_day_result,
                performance_management=pm_result,
                insight_of_week=insight_of_week
            )

        finally:
            session.close()
