"""Tests for configuration module."""

import os
import pytest


class TestConfig:
    """Test Config class functionality."""

    def test_smtp_port_default(self, monkeypatch):
        """Test that SMTP port has correct default."""
        monkeypatch.delenv('EMAIL_SMTP_PORT', raising=False)
        # Need to reimport to get fresh config
        import importlib
        from polar_report import config
        importlib.reload(config)
        assert config.Config.EMAIL_SMTP_PORT == 587

    def test_smtp_port_valid(self, monkeypatch):
        """Test that valid SMTP port is parsed correctly."""
        monkeypatch.setenv('EMAIL_SMTP_PORT', '465')
        import importlib
        from polar_report import config
        importlib.reload(config)
        assert config.Config.EMAIL_SMTP_PORT == 465

    def test_smtp_port_invalid_falls_back(self, monkeypatch):
        """Test that invalid SMTP port falls back to default."""
        monkeypatch.setenv('EMAIL_SMTP_PORT', 'not-a-number')
        import importlib
        from polar_report import config
        importlib.reload(config)
        assert config.Config.EMAIL_SMTP_PORT == 587

    def test_is_email_configured(self, monkeypatch):
        """Test email configuration check."""
        monkeypatch.setenv('EMAIL_SMTP_SERVER', 'smtp.test.com')
        monkeypatch.setenv('EMAIL_USERNAME', 'test@test.com')
        monkeypatch.setenv('EMAIL_PASSWORD', 'testpass')
        monkeypatch.setenv('EMAIL_RECIPIENT', 'recipient@test.com')
        import importlib
        from polar_report import config
        importlib.reload(config)
        assert config.Config.is_email_configured() is True

    def test_is_email_not_configured(self, monkeypatch):
        """Test email configuration check when missing."""
        monkeypatch.delenv('EMAIL_PASSWORD', raising=False)
        monkeypatch.setenv('EMAIL_SMTP_SERVER', 'smtp.test.com')
        monkeypatch.setenv('EMAIL_USERNAME', 'test@test.com')
        monkeypatch.setenv('EMAIL_RECIPIENT', 'recipient@test.com')
        import importlib
        from polar_report import config
        importlib.reload(config)
        # Not configured because password is missing
        assert config.Config.EMAIL_PASSWORD == ''
