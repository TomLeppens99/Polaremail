"""
Weekly report generator.
Creates HTML email reports from aggregated Polar data.
"""

import logging
import os
from datetime import datetime, date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .aggregator import WeeklyAggregator, WeeklyReport, format_duration, format_distance
from .config import Config

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates HTML email reports from Polar data."""

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
        self.jinja_env.filters['format_duration'] = format_duration
        self.jinja_env.filters['format_distance'] = format_distance

        # Add global functions
        self.jinja_env.globals['format_duration'] = format_duration
        self.jinja_env.globals['format_distance'] = format_distance

    def generate_html(self, report: WeeklyReport, generation_time: datetime = None) -> str:
        """
        Generate HTML email content from a WeeklyReport.

        Args:
            report: WeeklyReport data object
            generation_time: Timestamp for the report (defaults to now)

        Returns:
            HTML string for the email body
        """
        if generation_time is None:
            generation_time = datetime.now()

        try:
            template = self.jinja_env.get_template('email_report.html')

            html = template.render(
                week_start=report.week_start,
                week_end=report.week_end,
                training=report.training,
                sleep=report.sleep,
                recovery=report.recovery,
                comparison=report.comparison,
                highlights=report.highlights,
                overall_rating=report.overall_rating,
                generation_time=generation_time
            )

            return html

        except Exception as e:
            logger.error(f"Failed to render email template: {e}")
            raise

    def generate_subject(self, report: WeeklyReport) -> str:
        """
        Generate email subject line.

        Args:
            report: WeeklyReport data object

        Returns:
            Email subject string
        """
        date_range = f"{report.week_start.strftime('%b %d')} - {report.week_end.strftime('%b %d')}"
        return f"Your Polar Training Report - Week of {date_range}"

    def generate_plain_text(self, report: WeeklyReport) -> str:
        """
        Generate plain text version of the report for email fallback.

        Args:
            report: WeeklyReport data object

        Returns:
            Plain text string
        """
        lines = [
            "POLAR TRAINING REPORT",
            f"Week of {report.week_start.strftime('%B %d')} - {report.week_end.strftime('%B %d, %Y')}",
            f"Overall: {report.overall_rating}",
            "",
            "=" * 50,
            "TRAINING SUMMARY",
            "=" * 50,
            f"Sessions: {report.training.total_sessions}",
            f"Duration: {format_duration(report.training.total_duration_seconds)}",
            f"Distance: {format_distance(report.training.total_distance_meters)}",
            f"Calories: {report.training.total_calories:,} kcal",
        ]

        if report.training.avg_heart_rate:
            lines.append(f"Avg Heart Rate: {report.training.avg_heart_rate:.0f} bpm")

        lines.extend([
            "",
            "=" * 50,
            "RECOVERY & SLEEP",
            "=" * 50,
        ])

        if report.recovery.avg_recharge_status:
            lines.append(f"Nightly Recharge: {report.recovery.avg_recharge_status:.1f}/5")

        if report.sleep.avg_sleep_score:
            lines.append(f"Sleep Score: {report.sleep.avg_sleep_score:.0f}/100")

        if report.sleep.avg_duration_hours:
            hours = int(report.sleep.avg_duration_hours)
            mins = int((report.sleep.avg_duration_hours % 1) * 60)
            lines.append(f"Avg Sleep Duration: {hours}h {mins}min")

        if report.recovery.avg_hrv:
            lines.append(f"Avg HRV: {report.recovery.avg_hrv:.0f} ms")

        if report.training.best_session:
            best_session = report.training.best_session
            sport = best_session.sport.replace('_', ' ').title() if best_session.sport else "Session"
            duration = format_duration(best_session.duration_seconds or 0)
            if best_session.distance_meters:
                duration += f" | {format_distance(best_session.distance_meters)}"
            if best_session.calories:
                duration += f" | {best_session.calories:,} kcal"
            lines.extend([
                "",
                "=" * 50,
                "BEST SESSION",
                "=" * 50,
                f"{sport}: {duration}"
            ])

        if report.sleep.best_night_date or report.sleep.worst_night_date:
            lines.extend([
                "",
                "=" * 50,
                "SLEEP INSIGHTS",
                "=" * 50,
            ])
            if report.sleep.best_night_date:
                lines.append(
                    f"Best Night: {report.sleep.best_night_date.strftime('%A')} "
                    f"({report.sleep.best_night_score:.0f}/100)"
                )
            if report.sleep.worst_night_date:
                lines.append(
                    f"Needs Work: {report.sleep.worst_night_date.strftime('%A')} "
                    f"({report.sleep.worst_night_score:.0f}/100)"
                )

        if report.recovery.best_day_date or report.recovery.worst_day_date or report.recovery.low_recharge_days:
            lines.extend([
                "",
                "=" * 50,
                "RECOVERY INSIGHTS",
                "=" * 50,
            ])
            if report.recovery.best_day_date:
                lines.append(
                    f"Best Recharge: {report.recovery.best_day_date.strftime('%A')} "
                    f"({report.recovery.best_day_status}/5)"
                )
            if report.recovery.worst_day_date:
                lines.append(
                    f"Lowest Recharge: {report.recovery.worst_day_date.strftime('%A')} "
                    f"({report.recovery.worst_day_status}/5)"
                )
            if report.recovery.low_recharge_days:
                low_days = ", ".join(day.strftime('%A') for day in report.recovery.low_recharge_days[:3])
                extra = ""
                if len(report.recovery.low_recharge_days) > 3:
                    extra = f" (+{len(report.recovery.low_recharge_days) - 3} more)"
                lines.append(f"Low Recharge Days: {low_days}{extra}")

        if report.highlights:
            lines.extend([
                "",
                "=" * 50,
                "HIGHLIGHTS",
                "=" * 50,
            ])

            for highlight in report.highlights:
                icon = "[+]" if highlight.type == 'achievement' else "[!]"
                lines.append(f"{icon} {highlight.message}")
                if highlight.details:
                    lines.append(f"    {highlight.details}")

        if report.training.sport_breakdown:
            lines.extend([
                "",
                "=" * 50,
                "SPORTS BREAKDOWN",
                "=" * 50,
            ])

            for sport, data in report.training.sport_breakdown.items():
                sport_name = sport.replace('_', ' ').title()
                distance_str = format_distance(data.total_distance_meters) if data.total_distance_meters > 0 else "-"
                lines.append(
                    f"{sport_name}: {data.session_count} sessions | "
                    f"{distance_str} | {format_duration(data.total_duration_seconds)}"
                )

        lines.extend([
            "",
            "-" * 50,
            "View more at https://flow.polar.com",
            "Polar Weekly Training Report"
        ])

        return "\n".join(lines)

    def save_report_to_file(self, report: WeeklyReport, output_dir: str = None) -> str:
        """
        Save HTML report to a file for debugging/preview.

        Args:
            report: WeeklyReport data object
            output_dir: Directory to save to (defaults to reports/ in project)

        Returns:
            Path to saved file
        """
        if output_dir is None:
            output_dir = Config.BASE_DIR / 'reports'

        os.makedirs(output_dir, exist_ok=True)

        filename = f"report_{report.week_start.isoformat()}_{report.week_end.isoformat()}.html"
        filepath = Path(output_dir) / filename

        html = self.generate_html(report)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Report saved to {filepath}")
        return str(filepath)


def generate_weekly_report(
    user_id: str = None,
    week_start: date = None,
    save_to_file: bool = False
) -> tuple:
    """
    Generate a complete weekly report.

    Args:
        user_id: Polar user ID (defaults to config)
        week_start: Start of week (Monday). Defaults to last completed week.
        save_to_file: Whether to save HTML to file

    Returns:
        Tuple of (subject, html_content, plain_text_content, report_object)
    """
    # Aggregate data
    aggregator = WeeklyAggregator(user_id=user_id)
    report = aggregator.generate_report(week_start=week_start)

    # Generate email content
    generator = ReportGenerator()
    subject = generator.generate_subject(report)
    html_content = generator.generate_html(report)
    plain_text = generator.generate_plain_text(report)

    # Optionally save to file
    if save_to_file:
        generator.save_report_to_file(report)

    return subject, html_content, plain_text, report


# Convenience function for CLI usage
def preview_report(week_start: date = None) -> str:
    """
    Generate and save a preview of the weekly report.

    Args:
        week_start: Start of week to generate report for

    Returns:
        Path to saved HTML file
    """
    aggregator = WeeklyAggregator()
    report = aggregator.generate_report(week_start=week_start)

    generator = ReportGenerator()
    filepath = generator.save_report_to_file(report)

    print(f"Report preview saved to: {filepath}")
    print(f"Week: {report.week_start} to {report.week_end}")
    print(f"Rating: {report.overall_rating}")
    print(f"Training sessions: {report.training.total_sessions}")

    return filepath
