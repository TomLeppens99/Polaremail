"""
OAuth2 authentication module for Polar Accesslink API.
Handles authorization flow, token management, and user registration.
"""

import base64
import logging
import os
from urllib.parse import urlencode
from typing import Optional, Tuple

import requests

from .config import Config
from .models import get_session, User

logger = logging.getLogger(__name__)


class PolarAuthError(Exception):
    """Custom exception for Polar authentication errors."""
    pass


class PolarAuth:
    """Handles OAuth2 authentication with Polar Accesslink API."""

    SCOPE = 'accesslink.read_all'
    AUTH_URL = 'https://flow.polar.com/oauth2/authorization'
    TOKEN_URL = 'https://polaraccesslink.com/v3/oauth2/token'
    API_BASE = 'https://www.polaraccesslink.com/v3'

    def __init__(self, client_id: str = None, client_secret: str = None, redirect_uri: str = None):
        """
        Initialize PolarAuth with credentials.

        Args:
            client_id: Polar API client ID (defaults to config)
            client_secret: Polar API client secret (defaults to config)
            redirect_uri: OAuth redirect URI (defaults to config)
        """
        self.client_id = client_id or Config.POLAR_CLIENT_ID
        self.client_secret = client_secret or Config.POLAR_CLIENT_SECRET
        self.redirect_uri = redirect_uri or Config.POLAR_REDIRECT_URI

        if not self.client_id or not self.client_secret:
            logger.warning("Polar API credentials not configured")

    def _get_basic_auth_header(self) -> dict:
        """Generate Basic Auth header for token requests."""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            'Authorization': f'Basic {encoded}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

    def get_authorization_url(self, state: str = None) -> str:
        """
        Generate the authorization URL for OAuth2 flow.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': self.SCOPE
        }

        if state:
            params['state'] = state

        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, authorization_code: str) -> Tuple[str, str]:
        """
        Exchange authorization code for access token.

        Args:
            authorization_code: The code received from Polar after user authorization

        Returns:
            Tuple of (access_token, user_id)

        Raises:
            PolarAuthError: If token exchange fails
        """
        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': self.redirect_uri
        }

        try:
            response = requests.post(
                self.TOKEN_URL,
                data=data,
                headers=self._get_basic_auth_header(),
                timeout=30
            )

            if response.status_code != 200:
                error_msg = f"Token exchange failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise PolarAuthError(error_msg)

            token_data = response.json()
            access_token = token_data.get('access_token')
            user_id = str(token_data.get('x_user_id', ''))

            if not access_token:
                raise PolarAuthError("No access token in response")

            logger.info(f"Successfully obtained access token for user {user_id}")
            return access_token, user_id

        except requests.RequestException as e:
            error_msg = f"Network error during token exchange: {e}"
            logger.error(error_msg)
            raise PolarAuthError(error_msg)

    def register_user(self, access_token: str) -> dict:
        """
        Register a user with Polar Accesslink.
        Required before accessing user data via webhooks/API.

        Args:
            access_token: User's access token

        Returns:
            User registration data from Polar

        Raises:
            PolarAuthError: If registration fails
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        try:
            # First check if user is already registered
            check_response = requests.get(
                f"{self.API_BASE}/users",
                headers=headers,
                timeout=30
            )

            if check_response.status_code == 200:
                logger.info("User already registered with Polar Accesslink")
                return check_response.json()

            # If not registered (404), register the user
            if check_response.status_code == 404:
                # POST to /v3/users to register
                register_response = requests.post(
                    f"{self.API_BASE}/users",
                    headers=headers,
                    json={},  # Empty body, Polar creates user from token
                    timeout=30
                )

                if register_response.status_code in [200, 201]:
                    logger.info("Successfully registered user with Polar Accesslink")
                    return register_response.json()
                else:
                    error_msg = f"User registration failed: {register_response.status_code} - {register_response.text}"
                    logger.error(error_msg)
                    raise PolarAuthError(error_msg)

            # Handle other status codes
            error_msg = f"Unexpected response checking user: {check_response.status_code}"
            logger.error(error_msg)
            raise PolarAuthError(error_msg)

        except requests.RequestException as e:
            error_msg = f"Network error during user registration: {e}"
            logger.error(error_msg)
            raise PolarAuthError(error_msg)

    def delete_user(self, access_token: str, user_id: str) -> bool:
        """
        Delete a user from Polar Accesslink (unlink their account).

        Args:
            access_token: User's access token
            user_id: Polar user ID

        Returns:
            True if deletion successful
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }

        try:
            response = requests.delete(
                f"{self.API_BASE}/users/{user_id}",
                headers=headers,
                timeout=30
            )

            if response.status_code == 204:
                logger.info(f"Successfully deleted user {user_id} from Polar Accesslink")
                return True
            else:
                logger.error(f"Failed to delete user: {response.status_code} - {response.text}")
                return False

        except requests.RequestException as e:
            logger.error(f"Network error during user deletion: {e}")
            return False

    def get_user_info(self, access_token: str) -> Optional[dict]:
        """
        Get user information from Polar.

        Args:
            access_token: User's access token

        Returns:
            User info dictionary or None if failed
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }

        try:
            response = requests.get(
                f"{self.API_BASE}/users",
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get user info: {response.status_code}")
                return None

        except requests.RequestException as e:
            logger.error(f"Network error getting user info: {e}")
            return None

    def save_user_to_db(self, polar_user_id: str, access_token: str, user_info: dict = None):
        """
        Save or update user in the database.

        Args:
            polar_user_id: Polar user ID
            access_token: User's access token
            user_info: Optional user info from Polar API
        """
        session = get_session()
        try:
            user = session.query(User).filter_by(polar_user_id=polar_user_id).first()

            if user:
                # Update existing user
                user.access_token = access_token
                if user_info:
                    user.first_name = user_info.get('first-name')
                    user.last_name = user_info.get('last-name')
                    user.email = user_info.get('email')
            else:
                # Create new user
                user = User(
                    polar_user_id=polar_user_id,
                    access_token=access_token,
                    first_name=user_info.get('first-name') if user_info else None,
                    last_name=user_info.get('last-name') if user_info else None,
                    email=user_info.get('email') if user_info else None
                )
                session.add(user)

            session.commit()
            logger.info(f"User {polar_user_id} saved to database")

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save user to database: {e}")
            raise
        finally:
            session.close()

    def save_token_to_env(self, access_token: str, user_id: str):
        """
        Save token and user ID to .env file for persistence.

        Args:
            access_token: User's access token
            user_id: Polar user ID
        """
        env_path = Config.BASE_DIR / '.env'

        # Read existing .env content
        env_content = {}
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key] = value

        # Update with new values
        env_content['POLAR_ACCESS_TOKEN'] = access_token
        env_content['POLAR_USER_ID'] = user_id

        # Write back
        with open(env_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")

        logger.info("Access token and user ID saved to .env file")


def setup_webhook(access_token: str = None) -> dict:
    """
    Set up webhook with Polar to receive data events.

    Args:
        access_token: Optional access token (uses config if not provided)

    Returns:
        Webhook registration response

    Raises:
        PolarAuthError: If webhook setup fails
    """
    if not Config.WEBHOOK_URL or not Config.WEBHOOK_SECRET:
        raise PolarAuthError("Webhook URL and secret must be configured")

    # Webhooks use Basic auth with client credentials
    headers = Config.get_polar_auth_header()
    headers['Content-Type'] = 'application/json'
    headers['Accept'] = 'application/json'

    webhook_data = {
        'events': ['EXERCISE', 'SLEEP', 'ACTIVITY_SUMMARY'],
        'url': Config.WEBHOOK_URL
    }

    try:
        # First check existing webhooks
        list_response = requests.get(
            f"{PolarAuth.API_BASE}/webhooks",
            headers=headers,
            timeout=30
        )

        if list_response.status_code == 200:
            webhooks = list_response.json().get('data', [])
            for wh in webhooks:
                if wh.get('url') == Config.WEBHOOK_URL:
                    logger.info("Webhook already registered")
                    return wh

        # Register new webhook
        response = requests.post(
            f"{PolarAuth.API_BASE}/webhooks",
            json=webhook_data,
            headers=headers,
            timeout=30
        )

        if response.status_code in [200, 201]:
            logger.info("Webhook registered successfully")
            return response.json()
        else:
            error_msg = f"Webhook registration failed: {response.status_code} - {response.text}"
            logger.error(error_msg)
            raise PolarAuthError(error_msg)

    except requests.RequestException as e:
        error_msg = f"Network error during webhook setup: {e}"
        logger.error(error_msg)
        raise PolarAuthError(error_msg)


def get_webhook_status() -> Optional[dict]:
    """Get current webhook configuration from Polar."""
    headers = Config.get_polar_auth_header()
    headers['Accept'] = 'application/json'

    try:
        response = requests.get(
            f"{PolarAuth.API_BASE}/webhooks",
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            return response.json()
        return None

    except requests.RequestException as e:
        logger.error(f"Failed to get webhook status: {e}")
        return None


def delete_webhook(webhook_id: str) -> bool:
    """Delete a webhook registration."""
    headers = Config.get_polar_auth_header()
    headers['Accept'] = 'application/json'

    try:
        response = requests.delete(
            f"{PolarAuth.API_BASE}/webhooks/{webhook_id}",
            headers=headers,
            timeout=30
        )

        return response.status_code == 204

    except requests.RequestException as e:
        logger.error(f"Failed to delete webhook: {e}")
        return False
