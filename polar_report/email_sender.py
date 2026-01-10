"""
Email sending functionality for weekly reports.
Uses SMTP (Gmail compatible) to deliver HTML emails.
"""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import date
from typing import Optional, List

from .config import Config
from .report import generate_weekly_report

logger = logging.getLogger(__name__)


class EmailSenderError(Exception):
    """Custom exception for email sending errors."""
    pass


class EmailSender:
    """Sends HTML emails via SMTP."""

    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = None,
        username: str = None,
        password: str = None
    ):
        """
        Initialize email sender.

        Args:
            smtp_server: SMTP server address (defaults to config)
            smtp_port: SMTP server port (defaults to config)
            username: SMTP username/email (defaults to config)
            password: SMTP password/app password (defaults to config)
        """
        self.smtp_server = smtp_server or Config.EMAIL_SMTP_SERVER
        self.smtp_port = smtp_port or Config.EMAIL_SMTP_PORT
        self.username = username or Config.EMAIL_USERNAME
        self.password = password or Config.EMAIL_PASSWORD
        self.from_name = Config.EMAIL_FROM_NAME

    def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        html_content: str,
        plain_text: str = None,
        attachments: List[tuple] = None
    ) -> bool:
        """
        Send an HTML email.

        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject line
            html_content: HTML body content
            plain_text: Plain text fallback (optional)
            attachments: List of (filename, content, mimetype) tuples

        Returns:
            True if email sent successfully

        Raises:
            EmailSenderError: If sending fails
        """
        if not self.username or not self.password:
            raise EmailSenderError("Email credentials not configured")

        if not to_addresses:
            raise EmailSenderError("No recipients specified")

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.from_name} <{self.username}>"
        msg['To'] = ', '.join(to_addresses)

        # Attach plain text version
        if plain_text:
            part_text = MIMEText(plain_text, 'plain', 'utf-8')
            msg.attach(part_text)

        # Attach HTML version
        part_html = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part_html)

        # Attach any files
        if attachments:
            for filename, content, mimetype in attachments:
                maintype, subtype = mimetype.split('/', 1)
                attachment = MIMEBase(maintype, subtype)
                attachment.set_payload(content)
                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{filename}"'
                )
                msg.attach(attachment)

        # Send email
        try:
            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(self.username, self.password)
                server.sendmail(self.username, to_addresses, msg.as_string())

            logger.info(f"Email sent successfully to {', '.join(to_addresses)}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed: {e}"
            logger.error(error_msg)
            raise EmailSenderError(error_msg)

        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {e}"
            logger.error(error_msg)
            raise EmailSenderError(error_msg)

        except Exception as e:
            error_msg = f"Failed to send email: {e}"
            logger.error(error_msg)
            raise EmailSenderError(error_msg)

    def test_connection(self) -> bool:
        """
        Test SMTP connection without sending an email.

        Returns:
            True if connection successful
        """
        try:
            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(self.username, self.password)

            logger.info("SMTP connection test successful")
            return True

        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False


def send_weekly_report(
    recipient: str = None,
    user_id: str = None,
    week_start: date = None
) -> bool:
    """
    Generate and send the weekly training report.

    Args:
        recipient: Email recipient (defaults to config)
        user_id: Polar user ID (defaults to config)
        week_start: Start of week (defaults to last completed week)

    Returns:
        True if email sent successfully
    """
    recipient = recipient or Config.EMAIL_RECIPIENT

    if not recipient:
        logger.error("No email recipient configured")
        return False

    try:
        # Generate report
        logger.info(f"Generating weekly report for week starting {week_start or 'last week'}")
        subject, html_content, plain_text, report = generate_weekly_report(
            user_id=user_id,
            week_start=week_start
        )

        # Send email
        sender = EmailSender()
        sender.send_email(
            to_addresses=[recipient],
            subject=subject,
            html_content=html_content,
            plain_text=plain_text
        )

        logger.info(f"Weekly report sent to {recipient}")
        logger.info(f"Report: {report.week_start} to {report.week_end}, Rating: {report.overall_rating}")

        return True

    except Exception as e:
        logger.error(f"Failed to send weekly report: {e}")
        return False


def send_test_email(recipient: str = None) -> bool:
    """
    Send a test email to verify configuration.

    Args:
        recipient: Email recipient (defaults to config)

    Returns:
        True if email sent successfully
    """
    recipient = recipient or Config.EMAIL_RECIPIENT

    if not recipient:
        logger.error("No email recipient configured")
        return False

    subject = "Polar Training Report - Test Email"
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; }
            .header { background: #e63946; color: white; padding: 20px; text-align: center; }
            .content { padding: 20px; background: #f9f9f9; }
            .success { color: #28a745; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Polar Training Report</h1>
            </div>
            <div class="content">
                <p class="success">Email configuration is working correctly!</p>
                <p>This is a test email from your Polar Weekly Report system.</p>
                <p>If you're seeing this, your email settings are properly configured.</p>
                <hr>
                <p><small>Configuration:</small></p>
                <ul>
                    <li>SMTP Server: {smtp_server}</li>
                    <li>SMTP Port: {smtp_port}</li>
                    <li>From: {from_email}</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """.format(
        smtp_server=Config.EMAIL_SMTP_SERVER,
        smtp_port=Config.EMAIL_SMTP_PORT,
        from_email=Config.EMAIL_USERNAME
    )

    plain_text = """
    Polar Training Report - Test Email

    Email configuration is working correctly!

    This is a test email from your Polar Weekly Report system.
    If you're seeing this, your email settings are properly configured.
    """

    try:
        sender = EmailSender()
        sender.send_email(
            to_addresses=[recipient],
            subject=subject,
            html_content=html_content,
            plain_text=plain_text
        )
        logger.info(f"Test email sent to {recipient}")
        return True

    except Exception as e:
        logger.error(f"Failed to send test email: {e}")
        return False
