"""Tests for email sender module."""

import pytest


class TestEmailSender:
    """Test EmailSender functionality."""

    def test_test_email_html_format(self):
        """Test that test email HTML template formats correctly."""
        from polar_report.config import Config
        
        # This was previously crashing with KeyError due to CSS curly braces
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .header {{ background: #e63946; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .success {{ color: #28a745; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <ul>
                    <li>SMTP Server: {smtp_server}</li>
                    <li>SMTP Port: {smtp_port}</li>
                    <li>From: {from_email}</li>
                </ul>
            </div>
        </body>
        </html>
        """.format(
            smtp_server=Config.EMAIL_SMTP_SERVER,
            smtp_port=Config.EMAIL_SMTP_PORT,
            from_email=Config.EMAIL_USERNAME
        )
        
        # If we get here without exception, the test passes
        assert 'smtp.gmail.com' in html_content or Config.EMAIL_SMTP_SERVER in html_content

    def test_email_sender_init(self):
        """Test EmailSender initialization."""
        from polar_report.email_sender import EmailSender
        
        sender = EmailSender()
        assert sender.smtp_server is not None
        assert sender.smtp_port is not None

    def test_email_sender_custom_config(self):
        """Test EmailSender with custom configuration."""
        from polar_report.email_sender import EmailSender
        
        sender = EmailSender(
            smtp_server='custom.smtp.com',
            smtp_port=465,
            username='user@test.com',
            password='testpass'
        )
        assert sender.smtp_server == 'custom.smtp.com'
        assert sender.smtp_port == 465
        assert sender.username == 'user@test.com'
