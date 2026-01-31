"""
Health Digest Report Generator.

Creates HTML email reports from Health Digest analysis data.
"""

import logging
import os
from datetime import datetime, date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .health_digest import HealthDigestCalculator, HealthDigestReport
from .chart_generator import generate_digest_charts, ChartGenerator
from .config import Config

logger = logging.getLogger(__name__)


class HealthDigestReportGenerator:
    """Generates HTML email reports from Health Digest data."""

    def __init__(self, template_dir: str = None):
        """
        Initialize report generator.

        Args:
            template_dir: Directory containing email templates
        """
        if template_dir is None:
            template_dir = Config.BASE_DIR / 'templates'

        self.template_dir = Path(template_dir)

        # Set up Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Add custom filters
        self.jinja_env.filters['format_acwr_status'] = self._format_acwr_status
        self.jinja_env.filters['format_quadrant'] = self._format_quadrant
        self.jinja_env.filters['format_form_status'] = self._format_form_status

    @staticmethod
    def _format_acwr_status(status: str) -> str:
        """Format ACWR status for display."""
        labels = {
            "undertrained": "Undertrained",
            "optimal": "Optimal Zone",
            "caution": "Caution",
            "danger": "Danger Zone"
        }
        return labels.get(status, status.title())

    @staticmethod
    def _format_quadrant(quadrant: str) -> str:
        """Format HRV quadrant for display."""
        labels = {
            "coping_well": "Coping Well",
            "adapting": "Adapting",
            "fatigued": "Fatigued",
            "maladaptation": "Maladaptation"
        }
        return labels.get(quadrant, quadrant.title())

    @staticmethod
    def _format_form_status(status: str) -> str:
        """Format form status for display."""
        labels = {
            "detrained": "Detrained",
            "race_ready": "Race Ready",
            "neutral": "Neutral",
            "tired": "Tired",
            "very_fatigued": "Very Fatigued"
        }
        return labels.get(status, status.title())

    def generate_html(
        self,
        report: HealthDigestReport,
        charts: dict = None
    ) -> str:
        """
        Generate HTML email content from a HealthDigestReport.

        Args:
            report: HealthDigestReport data object
            charts: Optional pre-generated chart URLs

        Returns:
            HTML string for the email body
        """
        # Generate charts if not provided
        if charts is None:
            charts = generate_digest_charts(report)

        try:
            template = self.jinja_env.get_template('email_health_digest.html')

            html = template.render(
                week_start=report.week_start,
                week_end=report.week_end,
                generation_time=report.generation_time,
                acwr=report.acwr,
                monotony_strain=report.monotony_strain,
                hrv_quadrant=report.hrv_quadrant,
                decoupling=report.decoupling,
                sleep_architecture=report.sleep_architecture,
                sleep_debt=report.sleep_debt,
                early_warning=report.early_warning,
                weather_performance=report.weather_performance,
                time_of_day=report.time_of_day,
                performance_management=report.performance_management,
                insight_of_week=report.insight_of_week,
                charts=charts
            )

            return html

        except Exception as e:
            logger.error(f"Failed to render health digest template: {e}")
            raise

    def generate_subject(self, report: HealthDigestReport) -> str:
        """
        Generate email subject line.

        Args:
            report: HealthDigestReport data object

        Returns:
            Email subject string
        """
        date_range = f"{report.week_start.strftime('%b %d')} - {report.week_end.strftime('%b %d')}"

        # Add key insight to subject
        if report.early_warning and report.early_warning.overall_status == "attention_needed":
            return f"⚠️ Health Digest - Week of {date_range}"
        elif report.acwr and report.acwr.status == "optimal":
            return f"✅ Health Digest - Week of {date_range}"
        else:
            return f"📊 Health Digest - Week of {date_range}"

    def generate_plain_text(self, report: HealthDigestReport) -> str:
        """
        Generate plain text version of the report for email fallback.

        Args:
            report: HealthDigestReport data object

        Returns:
            Plain text string
        """
        lines = [
            "WEEKLY HEALTH DIGEST",
            f"Week of {report.week_start.strftime('%B %d')} - {report.week_end.strftime('%B %d, %Y')}",
            "",
            "=" * 50,
        ]

        # Quick Stats
        lines.extend([
            "QUICK STATS",
            "=" * 50,
        ])

        if report.acwr:
            lines.append(f"ACWR: {report.acwr.acwr} ({self._format_acwr_status(report.acwr.status)})")

        if report.hrv_quadrant:
            lines.append(f"HRV Status: {self._format_quadrant(report.hrv_quadrant.quadrant)}")

        if report.performance_management:
            lines.append(f"Form (TSB): {report.performance_management.form_tsb}")

        if report.early_warning and report.early_warning.warnings:
            lines.append(f"Alerts: {len(report.early_warning.warnings)}")

        # Training Load
        lines.extend([
            "",
            "=" * 50,
            "TRAINING LOAD",
            "=" * 50,
        ])

        if report.acwr:
            lines.append(f"ACWR: {report.acwr.acwr} ({report.acwr.status})")
            lines.append(f"Acute Load: {report.acwr.acute_load}")
            lines.append(f"Chronic Load: {report.acwr.chronic_load}")
            lines.append(f"Trend: {report.acwr.trend}")

        if report.monotony_strain:
            lines.append(f"Monotony: {report.monotony_strain.monotony} ({report.monotony_strain.monotony_status})")
            lines.append(f"Weekly Load: {report.monotony_strain.weekly_total}")

        # Recovery
        lines.extend([
            "",
            "=" * 50,
            "RECOVERY STATUS",
            "=" * 50,
        ])

        if report.hrv_quadrant:
            lines.append(f"HRV: {report.hrv_quadrant.current_mean}ms (CV: {report.hrv_quadrant.current_cv}%)")
            lines.append(f"Status: {self._format_quadrant(report.hrv_quadrant.quadrant)}")
            lines.append(f"vs Baseline: {report.hrv_quadrant.mean_deviation_percent:+.1f}%")

        # Sleep
        lines.extend([
            "",
            "=" * 50,
            "SLEEP",
            "=" * 50,
        ])

        if report.sleep_architecture:
            lines.append(f"Duration: {report.sleep_architecture.avg_duration}")
            comp = report.sleep_architecture.composition
            lines.append(f"Deep: {comp.get('deep_percent', 0):.1f}%")
            lines.append(f"REM: {comp.get('rem_percent', 0):.1f}%")

        if report.sleep_debt:
            lines.append(f"Sleep Debt: {report.sleep_debt.recent_debt_hours}h ({report.sleep_debt.status})")

        # Early Warnings
        if report.early_warning and report.early_warning.warnings:
            lines.extend([
                "",
                "=" * 50,
                "EARLY WARNINGS",
                "=" * 50,
            ])
            for warning in report.early_warning.warnings:
                lines.append(f"[!] {warning.get('message', 'Warning')}")

        # Performance Management
        if report.performance_management:
            lines.extend([
                "",
                "=" * 50,
                "PERFORMANCE",
                "=" * 50,
                f"Fitness (CTL): {report.performance_management.fitness_ctl}",
                f"Fatigue (ATL): {report.performance_management.fatigue_atl}",
                f"Form (TSB): {report.performance_management.form_tsb}",
                f"Status: {self._format_form_status(report.performance_management.form_status)}",
            ])

        # Insight
        if report.insight_of_week:
            lines.extend([
                "",
                "=" * 50,
                "INSIGHT OF THE WEEK",
                "=" * 50,
                report.insight_of_week
            ])

        lines.extend([
            "",
            "-" * 50,
            "View more at https://flow.polar.com",
            "Weekly Health Digest"
        ])

        return "\n".join(lines)

    def save_report_to_file(
        self,
        report: HealthDigestReport,
        output_dir: str = None
    ) -> str:
        """
        Save HTML report to a file for debugging/preview.

        Args:
            report: HealthDigestReport data object
            output_dir: Directory to save to (defaults to reports/ in project)

        Returns:
            Path to saved file
        """
        if output_dir is None:
            output_dir = Config.BASE_DIR / 'reports'

        os.makedirs(output_dir, exist_ok=True)

        filename = f"health_digest_{report.week_start.isoformat()}_{report.week_end.isoformat()}.html"
        filepath = Path(output_dir) / filename

        html = self.generate_html(report)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Health Digest saved to {filepath}")
        return str(filepath)


def generate_health_digest(
    user_id: str = None,
    week_start: date = None,
    save_to_file: bool = False
) -> tuple:
    """
    Generate a complete Health Digest report.

    Args:
        user_id: Polar user ID (defaults to config)
        week_start: Start of week (Monday). Defaults to last completed week.
        save_to_file: Whether to save HTML to file

    Returns:
        Tuple of (subject, html_content, plain_text_content, report_object)
    """
    # Calculate digest data
    calculator = HealthDigestCalculator(user_id=user_id)
    report = calculator.generate_health_digest(week_start=week_start)

    # Generate email content
    generator = HealthDigestReportGenerator()
    subject = generator.generate_subject(report)
    html_content = generator.generate_html(report)
    plain_text = generator.generate_plain_text(report)

    # Optionally save to file
    if save_to_file:
        generator.save_report_to_file(report)

    return subject, html_content, plain_text, report


def preview_health_digest(week_start: date = None) -> str:
    """
    Generate and save a preview of the Health Digest.

    Args:
        week_start: Start of week to generate report for

    Returns:
        Path to saved HTML file
    """
    calculator = HealthDigestCalculator()
    report = calculator.generate_health_digest(week_start=week_start)

    generator = HealthDigestReportGenerator()
    filepath = generator.save_report_to_file(report)

    print(f"Health Digest preview saved to: {filepath}")
    print(f"Week: {report.week_start} to {report.week_end}")

    if report.acwr:
        print(f"ACWR: {report.acwr.acwr} ({report.acwr.status})")
    if report.hrv_quadrant:
        print(f"HRV: {report.hrv_quadrant.quadrant}")
    if report.performance_management:
        print(f"Form: {report.performance_management.form_tsb}")

    return filepath
