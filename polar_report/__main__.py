"""
Main entry point for Polar Weekly Report system.
Provides CLI interface for all functionality.
"""

import argparse
import logging
import sys
from datetime import datetime

from .config import Config


def setup_logging(level: str = None):
    """Configure logging for the application."""
    level = level or Config.LOG_LEVEL
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def cmd_auth(args):
    """Start the OAuth authentication server."""
    from .webhook import run_server

    print("\nPolar OAuth2 Authentication")
    print("=" * 40)
    print(f"1. Open your browser to: http://localhost:{args.port}/auth")
    print("2. Log in with your Polar account")
    print("3. Authorize the application")
    print("4. The callback will save your access token")
    print("\nStarting server...\n")

    run_server(host=args.host, port=args.port, debug=args.debug)


def cmd_webhook(args):
    """Run the webhook listener server."""
    from .webhook import run_server
    from .models import init_db

    init_db()

    print("\nPolar Webhook Listener")
    print("=" * 40)
    print(f"Listening on: http://{args.host}:{args.port}/webhook")
    print("\nEndpoints:")
    print("  POST /webhook - Receive Polar events")
    print("  GET  /status  - Check service status")
    print("  POST /sync    - Manually sync data")
    print("\nStarting server...\n")

    run_server(host=args.host, port=args.port, debug=args.debug)


def cmd_setup_webhook(args):
    """Register webhook with Polar."""
    from .auth import setup_webhook, get_webhook_status

    if args.status:
        status = get_webhook_status()
        if status:
            print("Current webhook configuration:")
            print(f"  {status}")
        else:
            print("No webhook configured or failed to fetch status")
        return

    print("\nRegistering webhook with Polar...")
    try:
        result = setup_webhook()
        print("Webhook registered successfully!")
        print(f"  ID: {result.get('id')}")
        print(f"  URL: {result.get('url')}")
        print(f"  Events: {result.get('events')}")
    except Exception as e:
        print(f"Failed to register webhook: {e}")
        sys.exit(1)


def cmd_sync(args):
    """Sync data from Polar API."""
    from .polar_api import PolarAPI
    from .models import init_db

    if not Config.POLAR_ACCESS_TOKEN:
        print("Error: Not authenticated with Polar")
        print("Run: python -m polar_report auth")
        sys.exit(1)

    init_db()

    print("\nSyncing data from Polar API...")
    api = PolarAPI()
    results = api.sync_all()

    print("Sync complete:")
    for data_type, count in results.items():
        print(f"  {data_type}: {count} new records")


def cmd_report(args):
    """Generate and optionally send the weekly report."""
    from .report import generate_weekly_report, ReportGenerator
    from .aggregator import WeeklyAggregator
    from .email_sender import send_weekly_report
    from .models import init_db
    from datetime import date

    if not Config.POLAR_USER_ID:
        print("Error: No Polar user ID configured")
        print("Run: python -m polar_report auth")
        sys.exit(1)

    init_db()

    # Parse week start if provided
    week_start = None
    if args.week:
        try:
            week_start = datetime.strptime(args.week, '%Y-%m-%d').date()
        except ValueError:
            print(f"Invalid date format: {args.week}")
            print("Use YYYY-MM-DD format")
            sys.exit(1)

    print("\nGenerating weekly report...")

    # Generate report
    subject, html, plain_text, report = generate_weekly_report(
        week_start=week_start,
        save_to_file=args.save
    )

    print(f"\nReport: {report.week_start} to {report.week_end}")
    print(f"Rating: {report.overall_rating}")
    print(f"Training sessions: {report.training.total_sessions}")

    if report.training.total_duration_seconds > 0:
        hours = report.training.total_duration_seconds / 3600
        print(f"Total training: {hours:.1f} hours")

    if report.highlights:
        print(f"\nHighlights ({len(report.highlights)}):")
        for h in report.highlights[:5]:
            icon = "[+]" if h.type == 'achievement' else "[!]"
            print(f"  {icon} {h.message}")

    if args.save:
        generator = ReportGenerator()
        filepath = generator.save_report_to_file(report)
        print(f"\nReport saved to: {filepath}")

    if args.send:
        print(f"\nSending report to {args.recipient or Config.EMAIL_RECIPIENT}...")
        success = send_weekly_report(recipient=args.recipient, week_start=week_start)
        if success:
            print("Email sent successfully!")
        else:
            print("Failed to send email")
            sys.exit(1)


def cmd_schedule(args):
    """Run the scheduler for automated reports."""
    from .scheduler import run_scheduler, get_next_report_time, ReportScheduler

    if args.next:
        next_time = get_next_report_time()
        print(f"Next report scheduled for: {next_time.strftime('%A, %B %d, %Y at %H:%M')}")
        return

    if args.run_now:
        print("Running report now...")
        scheduler = ReportScheduler(blocking=False)
        scheduler.run_now()
        return

    run_scheduler()


def cmd_test_email(args):
    """Send a test email."""
    from .email_sender import send_test_email, EmailSender

    if args.test_connection:
        print("Testing SMTP connection...")
        sender = EmailSender()
        if sender.test_connection():
            print("SMTP connection successful!")
        else:
            print("SMTP connection failed!")
            sys.exit(1)
        return

    print(f"Sending test email to {args.recipient or Config.EMAIL_RECIPIENT}...")
    success = send_test_email(recipient=args.recipient)

    if success:
        print("Test email sent successfully!")
    else:
        print("Failed to send test email")
        sys.exit(1)


def cmd_status(args):
    """Show system status and configuration."""
    from .models import get_session, Exercise, SleepRecord, NightlyRecharge, init_db

    print("\nPolar Weekly Report - System Status")
    print("=" * 50)

    # Configuration status
    print("\n[Configuration]")
    print(f"  Polar Client ID: {'Configured' if Config.POLAR_CLIENT_ID else 'Missing'}")
    print(f"  Polar Access Token: {'Configured' if Config.POLAR_ACCESS_TOKEN else 'Missing'}")
    print(f"  Polar User ID: {Config.POLAR_USER_ID or 'Not set'}")
    print(f"  Webhook URL: {Config.WEBHOOK_URL or 'Not configured'}")
    print(f"  Email: {'Configured' if Config.is_email_configured() else 'Not configured'}")

    # Schedule
    print("\n[Schedule]")
    print(f"  Report Day: {Config.REPORT_DAY}")
    print(f"  Report Time: {Config.REPORT_TIME}")
    print(f"  Timezone: {Config.TIMEZONE}")

    # Database status
    print("\n[Database]")
    try:
        init_db()
        session = get_session()
        exercises = session.query(Exercise).count()
        sleep = session.query(SleepRecord).count()
        recharge = session.query(NightlyRecharge).count()
        session.close()

        print(f"  Exercises: {exercises}")
        print(f"  Sleep Records: {sleep}")
        print(f"  Nightly Recharge: {recharge}")
    except Exception as e:
        print(f"  Error: {e}")

    # Next report time
    if Config.POLAR_USER_ID:
        from .scheduler import get_next_report_time
        next_time = get_next_report_time()
        print(f"\n[Next Report]")
        print(f"  {next_time.strftime('%A, %B %d, %Y at %H:%M %Z')}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Polar Weekly Training Report System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m polar_report auth              # Start OAuth flow
  python -m polar_report sync              # Sync data from Polar
  python -m polar_report report --save     # Generate and save report
  python -m polar_report report --send     # Generate and email report
  python -m polar_report schedule          # Start scheduled jobs
  python -m polar_report status            # Show system status
        """
    )

    parser.add_argument('-v', '--verbose', action='store_true', help='Enable debug logging')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # auth command
    auth_parser = subparsers.add_parser('auth', help='Start OAuth authentication')
    auth_parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    auth_parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    auth_parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    # webhook command
    webhook_parser = subparsers.add_parser('webhook', help='Run webhook listener')
    webhook_parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    webhook_parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    webhook_parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    # setup-webhook command
    setup_wh_parser = subparsers.add_parser('setup-webhook', help='Register webhook with Polar')
    setup_wh_parser.add_argument('--status', action='store_true', help='Show current webhook status')

    # sync command
    sync_parser = subparsers.add_parser('sync', help='Sync data from Polar API')

    # report command
    report_parser = subparsers.add_parser('report', help='Generate weekly report')
    report_parser.add_argument('--week', help='Week start date (YYYY-MM-DD)')
    report_parser.add_argument('--save', action='store_true', help='Save HTML to file')
    report_parser.add_argument('--send', action='store_true', help='Send via email')
    report_parser.add_argument('--recipient', help='Email recipient (overrides config)')

    # schedule command
    schedule_parser = subparsers.add_parser('schedule', help='Run scheduled jobs')
    schedule_parser.add_argument('--next', action='store_true', help='Show next scheduled time')
    schedule_parser.add_argument('--run-now', action='store_true', help='Run report immediately')

    # test-email command
    email_parser = subparsers.add_parser('test-email', help='Send test email')
    email_parser.add_argument('--recipient', help='Email recipient')
    email_parser.add_argument('--test-connection', action='store_true', help='Test SMTP connection only')

    # status command
    status_parser = subparsers.add_parser('status', help='Show system status')

    args = parser.parse_args()

    # Setup logging
    setup_logging('DEBUG' if args.verbose else None)

    # Handle commands
    if args.command == 'auth':
        cmd_auth(args)
    elif args.command == 'webhook':
        cmd_webhook(args)
    elif args.command == 'setup-webhook':
        cmd_setup_webhook(args)
    elif args.command == 'sync':
        cmd_sync(args)
    elif args.command == 'report':
        cmd_report(args)
    elif args.command == 'schedule':
        cmd_schedule(args)
    elif args.command == 'test-email':
        cmd_test_email(args)
    elif args.command == 'status':
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
