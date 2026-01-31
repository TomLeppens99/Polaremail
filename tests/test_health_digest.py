"""Tests for Health Digest module."""

import statistics
from datetime import date, datetime, timedelta

import pytest

from polar_report.health_digest import (
    HealthDigestCalculator,
    ACWRResult,
    MonotonyStrainResult,
    HRVQuadrantResult,
    SleepArchitectureResult,
    SleepDebtResult,
    EarlyWarningResult,
    TimeOfDayResult,
    PerformanceManagementResult,
)


class TestTRIMPCalculation:
    """Test TRIMP calculation."""

    def test_trimp_basic_male(self):
        """Test basic TRIMP calculation for male."""
        calc = HealthDigestCalculator(user_id='test')
        trimp = calc.calculate_trimp(
            duration_min=60,
            hr_avg=140,
            hr_rest=60,
            hr_max=180,
            gender='male'
        )
        # TRIMP should be positive
        assert trimp > 0
        # For 60 min at moderate intensity, expect reasonable value
        assert 50 < trimp < 200

    def test_trimp_basic_female(self):
        """Test basic TRIMP calculation for female."""
        calc = HealthDigestCalculator(user_id='test')
        trimp = calc.calculate_trimp(
            duration_min=60,
            hr_avg=140,
            hr_rest=60,
            hr_max=180,
            gender='female'
        )
        # TRIMP should be positive but lower than male (different coefficient)
        assert trimp > 0

    def test_trimp_zero_duration(self):
        """Test TRIMP with zero duration."""
        calc = HealthDigestCalculator(user_id='test')
        trimp = calc.calculate_trimp(
            duration_min=0,
            hr_avg=140,
            hr_rest=60,
            hr_max=180,
            gender='male'
        )
        assert trimp == 0

    def test_trimp_invalid_hr(self):
        """Test TRIMP with invalid heart rate range."""
        calc = HealthDigestCalculator(user_id='test')
        trimp = calc.calculate_trimp(
            duration_min=60,
            hr_avg=140,
            hr_rest=180,  # Rest higher than max
            hr_max=180,
            gender='male'
        )
        assert trimp == 0


class TestEWMACalculation:
    """Test EWMA calculation."""

    def test_ewma_single_value(self):
        """Test EWMA with single value."""
        calc = HealthDigestCalculator(user_id='test')
        ewma = calc.calculate_ewma([100], 7)
        assert ewma == 100

    def test_ewma_constant_values(self):
        """Test EWMA with constant values."""
        calc = HealthDigestCalculator(user_id='test')
        ewma = calc.calculate_ewma([100, 100, 100, 100, 100], 7)
        assert ewma == 100

    def test_ewma_increasing_values(self):
        """Test EWMA with increasing values."""
        calc = HealthDigestCalculator(user_id='test')
        values = [10, 20, 30, 40, 50, 60, 70]
        ewma = calc.calculate_ewma(values, 7)
        # EWMA should be between first and last value
        assert 10 < ewma < 70

    def test_ewma_empty_list(self):
        """Test EWMA with empty list."""
        calc = HealthDigestCalculator(user_id='test')
        ewma = calc.calculate_ewma([], 7)
        assert ewma == 0


class TestMonotonyStrain:
    """Test Training Monotony & Strain calculation."""

    def test_monotony_good_variation(self):
        """Test monotony with good variation."""
        calc = HealthDigestCalculator(user_id='test')
        # High variation = low monotony
        loads = [100, 0, 150, 50, 200, 0, 100]
        result = calc.calculate_monotony_strain(loads)

        assert result is not None
        assert result.monotony < 1.5
        assert result.monotony_status == "good"

    def test_monotony_low_variation(self):
        """Test monotony with low variation (high risk)."""
        calc = HealthDigestCalculator(user_id='test')
        # Low variation = high monotony
        loads = [100, 100, 100, 100, 100, 100, 100]
        result = calc.calculate_monotony_strain(loads)

        assert result is not None
        # All same values = infinite monotony (or very high)
        assert result.monotony > 2.0 or result.monotony == 99.99
        assert result.monotony_status == "high_risk"

    def test_monotony_insufficient_data(self):
        """Test monotony with insufficient data."""
        calc = HealthDigestCalculator(user_id='test')
        result = calc.calculate_monotony_strain([100])
        assert result is None

    def test_strain_calculation(self):
        """Test strain is calculated correctly."""
        calc = HealthDigestCalculator(user_id='test')
        loads = [100, 50, 150, 75, 125, 25, 175]
        result = calc.calculate_monotony_strain(loads)

        expected_weekly_total = sum(loads)
        assert result.weekly_total == expected_weekly_total
        # Strain = weekly_total * monotony (but may have rounding at different levels)
        # Just verify strain is positive and in the expected range
        assert result.strain > 0
        # Allow for small rounding differences (within 1%)
        expected_strain = result.weekly_total * result.monotony
        assert abs(result.strain - expected_strain) < expected_strain * 0.01


class TestHRVQuadrant:
    """Test HRV Quadrant Analysis."""

    def test_hrv_coping_well(self):
        """Test HRV quadrant: coping well."""
        calc = HealthDigestCalculator(user_id='test')
        # High HRV (at baseline) + Low CV
        current = [50, 51, 49, 50, 52, 49, 51]  # Low CV
        baseline = [50] * 60  # Same as current

        result = calc.analyze_hrv_trends(current, baseline)

        assert result is not None
        assert result.quadrant == "coping_well"

    def test_hrv_fatigued(self):
        """Test HRV quadrant: fatigued."""
        calc = HealthDigestCalculator(user_id='test')
        # Low HRV + High CV
        current = [35, 45, 30, 50, 35, 40, 45]  # High CV, low mean
        baseline = [50] * 60  # Higher baseline

        result = calc.analyze_hrv_trends(current, baseline)

        assert result is not None
        assert result.quadrant == "fatigued"

    def test_hrv_insufficient_baseline(self):
        """Test HRV with insufficient baseline."""
        calc = HealthDigestCalculator(user_id='test')
        current = [50, 51, 49, 50, 52, 49, 51]
        baseline = [50] * 10  # Too short

        result = calc.analyze_hrv_trends(current, baseline)
        assert result is None


class TestSleepArchitecture:
    """Test Sleep Architecture Analysis."""

    def test_sleep_architecture_healthy(self):
        """Test healthy sleep architecture."""
        calc = HealthDigestCalculator(user_id='test')

        # Create mock sleep records
        class MockSleep:
            def __init__(self, total, deep, rem, light):
                self.duration_seconds = total * 60
                self.deep_sleep_seconds = deep * 60
                self.rem_sleep_seconds = rem * 60
                self.light_sleep_seconds = light * 60

        # Healthy sleep: 7.5h total, 20% deep, 22% REM
        records = [
            MockSleep(450, 90, 99, 261),  # 7.5h, 20% deep, 22% REM
            MockSleep(450, 90, 99, 261),
            MockSleep(450, 90, 99, 261),
        ]

        result = calc.analyze_sleep_architecture(records)

        assert result is not None
        assert result.avg_duration_hours > 7
        assert result.composition["deep_percent"] >= 15
        assert result.composition["rem_percent"] >= 20

    def test_sleep_architecture_deficits(self):
        """Test sleep architecture with deficits."""
        calc = HealthDigestCalculator(user_id='test')

        class MockSleep:
            def __init__(self, total, deep, rem, light):
                self.duration_seconds = total * 60
                self.deep_sleep_seconds = deep * 60
                self.rem_sleep_seconds = rem * 60
                self.light_sleep_seconds = light * 60

        # Poor sleep: 6h total, 10% deep, 15% REM
        records = [
            MockSleep(360, 36, 54, 270),
            MockSleep(360, 36, 54, 270),
        ]

        result = calc.analyze_sleep_architecture(records)

        assert result is not None
        assert result.deficits["deep_deficit_nights"] > 0
        assert result.deficits["rem_deficit_nights"] > 0


class TestSleepDebt:
    """Test Sleep Debt Tracker."""

    def test_sleep_debt_none(self):
        """Test no sleep debt."""
        calc = HealthDigestCalculator(user_id='test')

        class MockSleep:
            def __init__(self, hours):
                self.duration_seconds = hours * 3600

        # 8+ hours each night
        records = [MockSleep(8.5) for _ in range(7)]

        result = calc.calculate_sleep_debt(records, optimal_hours=8.0)

        assert result is not None
        assert result.recent_debt_hours <= 0
        assert result.status == "none"

    def test_sleep_debt_moderate(self):
        """Test moderate sleep debt."""
        calc = HealthDigestCalculator(user_id='test')

        class MockSleep:
            def __init__(self, hours):
                self.duration_seconds = hours * 3600

        # 6h each night (2h deficit per night)
        records = [MockSleep(6.0) for _ in range(7)]

        result = calc.calculate_sleep_debt(records, optimal_hours=8.0)

        assert result is not None
        assert result.recent_debt_hours > 0
        assert result.status in ["moderate", "severe"]


class TestEarlyWarning:
    """Test Early Warning System."""

    def test_early_warning_clear(self):
        """Test no warnings when vitals normal."""
        calc = HealthDigestCalculator(user_id='test')

        class MockRecharge:
            def __init__(self, hr, hrv):
                self.heart_rate_avg = hr
                self.hrv_avg = hrv

        # Baseline: HR=55, HRV=50
        baseline = [MockRecharge(55, 50) for _ in range(30)]
        # Recent: same as baseline
        recent = [MockRecharge(55, 50) for _ in range(7)]

        result = calc.check_early_warnings(recent, baseline)

        assert result.overall_status == "clear"
        assert len(result.warnings) == 0

    def test_early_warning_elevated_hr(self):
        """Test warning for elevated resting HR."""
        calc = HealthDigestCalculator(user_id='test')

        class MockRecharge:
            def __init__(self, hr, hrv):
                self.heart_rate_avg = hr
                self.hrv_avg = hrv

        # Baseline: HR=55
        baseline = [MockRecharge(55, 50) for _ in range(30)]
        # Recent: elevated HR (+10 bpm)
        recent = [MockRecharge(65, 50) for _ in range(7)]

        result = calc.check_early_warnings(recent, baseline)

        assert result.overall_status == "attention_needed"
        assert len(result.warnings) > 0
        assert any(w["type"] == "elevated_rhr" for w in result.warnings)


class TestTimeOfDay:
    """Test Time-of-Day Performance Analysis."""

    def test_time_of_day_analysis(self):
        """Test time of day analysis with varied data."""
        calc = HealthDigestCalculator(user_id='test')

        class MockExercise:
            def __init__(self, hour, distance, duration, hr):
                self.start_time = datetime(2025, 1, 15, hour, 0, 0)
                self.distance_meters = distance
                self.duration_seconds = duration
                self.average_heart_rate = hr

        # Create exercises at different times (need at least 10 total)
        exercises = [
            # Early morning sessions (slower)
            MockExercise(7, 5000, 1800, 150),
            MockExercise(7, 5000, 1800, 150),
            MockExercise(7, 5000, 1800, 150),
            MockExercise(7, 5000, 1850, 150),
            MockExercise(7, 5000, 1750, 150),
            # Afternoon sessions (faster)
            MockExercise(15, 5000, 1500, 145),
            MockExercise(15, 5000, 1500, 145),
            MockExercise(15, 5000, 1500, 145),
            MockExercise(15, 5000, 1550, 145),
            MockExercise(15, 5000, 1450, 145),
        ]

        result = calc.analyze_time_of_day_performance(exercises)

        assert result is not None
        assert result.optimal_slot == "afternoon"


class TestPerformanceManagement:
    """Test Performance Management Chart calculations."""

    def test_pmc_basic(self):
        """Test basic PMC calculation."""
        calc = HealthDigestCalculator(user_id='test')

        # 42 days of consistent training
        loads = [100] * 42

        result = calc.calculate_performance_management(loads)

        assert result is not None
        assert result.fitness_ctl > 0
        assert result.fatigue_atl > 0
        # TSB should be around 0 for consistent training
        assert -20 < result.form_tsb < 20

    def test_pmc_increasing_load(self):
        """Test PMC with increasing load."""
        calc = HealthDigestCalculator(user_id='test')

        # Increasing load over 42 days
        loads = [50 + i * 2 for i in range(42)]

        result = calc.calculate_performance_management(loads)

        assert result is not None
        # ATL should be higher than CTL (fatigue building)
        assert result.fatigue_atl > result.fitness_ctl * 0.9
        # TSB should be negative (tired)
        assert result.form_tsb < 0

    def test_pmc_taper(self):
        """Test PMC with taper (decreasing load)."""
        calc = HealthDigestCalculator(user_id='test')

        # High load then taper
        loads = [150] * 35 + [50] * 7

        result = calc.calculate_performance_management(loads)

        assert result is not None
        # CTL should still be relatively high
        assert result.fitness_ctl > 50
        # TSB should be increasing (form improving)


class TestACWR:
    """Test ACWR calculation."""

    def test_acwr_optimal(self):
        """Test ACWR in optimal range."""
        calc = HealthDigestCalculator(user_id='test')

        # Consistent moderate training
        class MockExercise:
            def __init__(self, day_offset, load):
                self.start_time = datetime.now() - timedelta(days=day_offset)
                self.training_load_cardio = load
                self.average_heart_rate = None
                self.duration_seconds = None

        # Create exercises with consistent load
        exercises = []
        for i in range(28):
            exercises.append(MockExercise(i + 1, 50))

        result = calc.calculate_acwr(exercises)

        assert result is not None
        # ACWR should be around 1.0 for consistent training
        assert 0.8 <= result.acwr <= 1.3
        assert result.status == "optimal"

    def test_acwr_undertrained(self):
        """Test ACWR when undertrained."""
        calc = HealthDigestCalculator(user_id='test')

        class MockExercise:
            def __init__(self, day_offset, load):
                self.start_time = datetime.now() - timedelta(days=day_offset)
                self.training_load_cardio = load
                self.average_heart_rate = None
                self.duration_seconds = None

        # High chronic load, low acute load
        exercises = []
        for i in range(7):
            exercises.append(MockExercise(i + 1, 20))  # Low recent
        for i in range(7, 28):
            exercises.append(MockExercise(i + 1, 100))  # High historic

        result = calc.calculate_acwr(exercises)

        assert result is not None
        assert result.acwr < 0.8
        assert result.status == "undertrained"


class TestChartGenerator:
    """Test chart generation."""

    def test_chart_url_generation(self):
        """Test that chart URLs are generated correctly."""
        from polar_report.chart_generator import ChartGenerator

        gen = ChartGenerator()

        url = gen.generate_acwr_gauge(1.15, "optimal")

        assert url.startswith("https://quickchart.io/chart")
        assert "c=" in url

    def test_pmc_chart_url(self):
        """Test PMC chart URL generation."""
        from polar_report.chart_generator import ChartGenerator

        gen = ChartGenerator()

        dates = ["W1", "W2", "W3", "W4"]
        ctl = [50, 55, 60, 65]
        atl = [60, 65, 55, 50]
        tsb = [-10, -10, 5, 15]

        url = gen.generate_pmc_chart(dates, ctl, atl, tsb)

        assert url.startswith("https://quickchart.io/chart")
