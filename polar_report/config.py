"""
Configuration management for Polar Weekly Report System.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class Config:
    """Application configuration loaded from environment variables."""

    # Base paths
    BASE_DIR = Path(__file__).parent.parent

    # Polar API Configuration
    POLAR_CLIENT_ID = os.getenv('POLAR_CLIENT_ID', '')
    POLAR_CLIENT_SECRET = os.getenv('POLAR_CLIENT_SECRET', '')
    POLAR_REDIRECT_URI = os.getenv('POLAR_REDIRECT_URI', 'http://localhost:5000/callback')
    POLAR_USER_ID = os.getenv('POLAR_USER_ID', '')
    POLAR_ACCESS_TOKEN = os.getenv('POLAR_ACCESS_TOKEN', '')

    # Polar API Endpoints
    POLAR_API_BASE = 'https://www.polaraccesslink.com'
    POLAR_AUTH_URL = 'https://flow.polar.com/oauth2/authorization'
    POLAR_TOKEN_URL = 'https://polaraccesslink.com/v3/oauth2/token'

    # Email Configuration
    EMAIL_SMTP_SERVER = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
    EMAIL_SMTP_PORT = int(os.getenv('EMAIL_SMTP_PORT', '587'))
    EMAIL_USERNAME = os.getenv('EMAIL_USERNAME', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT', '')
    EMAIL_FROM_NAME = os.getenv('EMAIL_FROM_NAME', 'Polar Training Report')

    # Webhook Configuration
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')

    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR}/polar_data.db')

    # Schedule Configuration
    REPORT_DAY = os.getenv('REPORT_DAY', 'Monday')
    REPORT_TIME = os.getenv('REPORT_TIME', '08:00')
    TIMEZONE = os.getenv('TIMEZONE', 'Europe/Brussels')

    # Flask Configuration
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    @classmethod
    def get_polar_auth_header(cls) -> dict:
        """Get Basic Auth header for Polar API (client credentials)."""
        import base64
        credentials = f"{cls.POLAR_CLIENT_ID}:{cls.POLAR_CLIENT_SECRET}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {'Authorization': f'Basic {encoded}'}

    @classmethod
    def get_polar_bearer_header(cls) -> dict:
        """Get Bearer token header for Polar API (user access)."""
        return {
            'Authorization': f'Bearer {cls.POLAR_ACCESS_TOKEN}',
            'Accept': 'application/json'
        }

    @classmethod
    def validate(cls) -> list:
        """Validate required configuration. Returns list of missing fields."""
        missing = []

        if not cls.POLAR_CLIENT_ID:
            missing.append('POLAR_CLIENT_ID')
        if not cls.POLAR_CLIENT_SECRET:
            missing.append('POLAR_CLIENT_SECRET')

        return missing

    @classmethod
    def is_email_configured(cls) -> bool:
        """Check if email settings are properly configured."""
        return all([
            cls.EMAIL_SMTP_SERVER,
            cls.EMAIL_USERNAME,
            cls.EMAIL_PASSWORD,
            cls.EMAIL_RECIPIENT
        ])

    @classmethod
    def is_webhook_configured(cls) -> bool:
        """Check if webhook settings are properly configured."""
        return all([
            cls.WEBHOOK_URL,
            cls.WEBHOOK_SECRET
        ])


# Convenience instance
config = Config()
