"""
Polar Accesslink API client for fetching fitness data.
Handles exercise, sleep, nightly recharge, and activity data retrieval.
"""

import logging
import re
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

import requests
from dateutil import parser as date_parser

from .config import Config
from .models import (
    get_session, Exercise, SleepRecord, NightlyRecharge,
    ActivitySummary, init_db
)

logger = logging.getLogger(__name__)


class PolarAPIError(Exception):
    """Custom exception for Polar API errors."""
    pass


class PolarAPI:
    """Client for Polar Accesslink API."""

    BASE_URL = 'https://www.polaraccesslink.com/v3'

    def __init__(self, access_token: str = None, user_id: str = None):
        """
        Initialize API client.

        Args:
            access_token: User's access token (defaults to config)
            user_id: Polar user ID (defaults to config)
        """
        self.access_token = access_token or Config.POLAR_ACCESS_TOKEN
        self.user_id = user_id or Config.POLAR_USER_ID

    def _get_headers(self) -> dict:
        """Get authorization headers."""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make an API request with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            PolarAPIError: If request fails
        """
        url = f"{self.BASE_URL}{endpoint}"
        kwargs.setdefault('headers', self._get_headers())
        kwargs.setdefault('timeout', 30)

        try:
            response = requests.request(method, url, **kwargs)

            if response.status_code == 401:
                raise PolarAPIError("Authentication failed - check access token")
            elif response.status_code == 403:
                raise PolarAPIError("Access forbidden - user may not be registered")
            elif response.status_code == 429:
                raise PolarAPIError("Rate limit exceeded - try again later")
            elif response.status_code >= 500:
                raise PolarAPIError(f"Polar server error: {response.status_code}")

            return response

        except requests.RequestException as e:
            raise PolarAPIError(f"Network error: {e}")

    @staticmethod
    def parse_iso_duration(duration_str: str) -> int:
        """
        Parse ISO-8601 duration to seconds.

        Args:
            duration_str: Duration in format PT1H23M45S

        Returns:
            Duration in seconds
        """
        if not duration_str:
            return 0

        # Pattern for ISO 8601 duration
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?'
        match = re.match(pattern, duration_str)

        if not match:
            logger.warning(f"Could not parse duration: {duration_str}")
            return 0

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = float(match.group(3) or 0)

        return int(hours * 3600 + minutes * 60 + seconds)

    def get_exercises(self, samples: bool = True, zones: bool = True) -> List[dict]:
        """
        Get exercises from Polar API (30-day window).

        Args:
            samples: Include sample data (GPS, HR samples)
            zones: Include heart rate zone data

        Returns:
            List of exercise dictionaries
        """
        params = {}
        if samples:
            params['samples'] = 'true'
        if zones:
            params['zones'] = 'true'

        response = self._make_request('GET', '/exercises', params=params)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            return []
        else:
            logger.error(f"Failed to get exercises: {response.status_code}")
            return []

    def get_exercise_details(self, exercise_id: str) -> Optional[dict]:
        """Get detailed data for a specific exercise."""
        response = self._make_request('GET', f'/exercises/{exercise_id}')

        if response.status_code == 200:
            return response.json()
        return None

    def get_sleep_data(self) -> List[dict]:
        """
        Get sleep data from Polar API (28-day window).

        Returns:
            List of sleep record dictionaries
        """
        response = self._make_request('GET', '/users/sleep')

        if response.status_code == 200:
            data = response.json()
            return data.get('nights', [])
        elif response.status_code == 204:
            return []
        else:
            logger.error(f"Failed to get sleep data: {response.status_code}")
            return []

    def get_nightly_recharge(self) -> List[dict]:
        """
        Get Nightly Recharge (recovery) data from Polar API.

        Returns:
            List of nightly recharge dictionaries
        """
        response = self._make_request('GET', '/users/nightly-recharge')

        if response.status_code == 200:
            data = response.json()
            return data.get('recharges', [])
        elif response.status_code == 204:
            return []
        else:
            logger.error(f"Failed to get nightly recharge: {response.status_code}")
            return []

    def get_activities(self, from_date: date, to_date: date) -> List[dict]:
        """
        Get daily activity summaries (365-day window with date range).

        Args:
            from_date: Start date
            to_date: End date

        Returns:
            List of activity summary dictionaries
        """
        params = {
            'from': from_date.isoformat(),
            'to': to_date.isoformat()
        }

        response = self._make_request('GET', '/users/activity-transactions', params=params)

        if response.status_code == 200:
            data = response.json()
            return data.get('activity-log', [])
        elif response.status_code == 204:
            return []
        else:
            logger.error(f"Failed to get activities: {response.status_code}")
            return []

    def sync_exercises_to_db(self) -> int:
        """
        Sync exercises from API to database.

        Returns:
            Number of exercises synced
        """
        exercises = self.get_exercises()
        session = get_session()
        count = 0

        try:
            for ex_data in exercises:
                polar_id = str(ex_data.get('id', ''))
                if not polar_id:
                    continue

                # Check if already exists
                existing = session.query(Exercise).filter_by(
                    polar_exercise_id=polar_id
                ).first()

                if existing:
                    continue

                # Parse heart rate zones
                hr_zones = {}
                if 'heart_rate' in ex_data and 'zones' in ex_data['heart_rate']:
                    for i, zone in enumerate(ex_data['heart_rate']['zones'], 1):
                        zone_duration = self.parse_iso_duration(zone.get('in_zone', 'PT0S'))
                        hr_zones[f'zone{i}'] = zone_duration

                # Create exercise record
                exercise = Exercise(
                    polar_exercise_id=polar_id,
                    user_id=self.user_id,
                    sport=ex_data.get('sport'),
                    start_time=date_parser.parse(ex_data['start_time']) if ex_data.get('start_time') else None,
                    duration_seconds=self.parse_iso_duration(ex_data.get('duration', '')),
                    duration_iso=ex_data.get('duration'),
                    distance_meters=ex_data.get('distance'),
                    calories=ex_data.get('calories'),
                    average_heart_rate=ex_data.get('heart_rate', {}).get('average'),
                    max_heart_rate=ex_data.get('heart_rate', {}).get('maximum'),
                    heart_rate_zones=hr_zones if hr_zones else None,
                    training_load_cardio=ex_data.get('training_load', {}).get('cardio_load'),
                    training_load_muscle=ex_data.get('training_load', {}).get('muscle_load'),
                    ascent_meters=ex_data.get('ascent'),
                    descent_meters=ex_data.get('descent'),
                    running_index=ex_data.get('running_index', {}).get('value'),
                    raw_payload=ex_data,
                    source='api'
                )

                session.add(exercise)
                count += 1

            session.commit()
            logger.info(f"Synced {count} exercises from API")

        except Exception as e:
            session.rollback()
            logger.error(f"Error syncing exercises: {e}")
            raise
        finally:
            session.close()

        return count

    def sync_sleep_to_db(self) -> int:
        """
        Sync sleep data from API to database.

        Returns:
            Number of sleep records synced
        """
        sleep_data = self.get_sleep_data()
        session = get_session()
        count = 0

        try:
            for sleep in sleep_data:
                sleep_date_str = sleep.get('date')
                if not sleep_date_str:
                    continue

                sleep_date = date_parser.parse(sleep_date_str).date()

                # Check if already exists
                existing = session.query(SleepRecord).filter_by(
                    user_id=self.user_id,
                    sleep_date=sleep_date
                ).first()

                if existing:
                    continue

                # Parse sleep stages (hypnogram)
                light_seconds = 0
                deep_seconds = 0
                rem_seconds = 0
                wake_seconds = 0

                # Hypnogram contains array of sleep stages with durations
                for stage in sleep.get('hypnogram', []):
                    stage_type = stage.get('sleep_stage')
                    duration = self.parse_iso_duration(stage.get('duration', 'PT0S'))

                    if stage_type == 1:  # REM
                        rem_seconds += duration
                    elif stage_type == 2:  # Light
                        light_seconds += duration
                    elif stage_type == 3:  # Deep
                        deep_seconds += duration
                    elif stage_type == 0:  # Wake
                        wake_seconds += duration

                record = SleepRecord(
                    user_id=self.user_id,
                    sleep_date=sleep_date,
                    sleep_start=date_parser.parse(sleep['sleep_start_time']) if sleep.get('sleep_start_time') else None,
                    sleep_end=date_parser.parse(sleep['sleep_end_time']) if sleep.get('sleep_end_time') else None,
                    duration_seconds=self.parse_iso_duration(sleep.get('duration', '')),
                    light_sleep_seconds=light_seconds,
                    deep_sleep_seconds=deep_seconds,
                    rem_sleep_seconds=rem_seconds,
                    wake_seconds=wake_seconds,
                    sleep_score=sleep.get('sleep_score'),
                    sleep_continuity=sleep.get('continuity'),
                    sleep_cycles=sleep.get('sleep_cycles'),
                    average_heart_rate=sleep.get('heart_rate_avg'),
                    min_heart_rate=sleep.get('heart_rate_min'),
                    average_breathing_rate=sleep.get('breathing_rate_avg'),
                    raw_payload=sleep,
                    source='api'
                )

                session.add(record)
                count += 1

            session.commit()
            logger.info(f"Synced {count} sleep records from API")

        except Exception as e:
            session.rollback()
            logger.error(f"Error syncing sleep: {e}")
            raise
        finally:
            session.close()

        return count

    def sync_nightly_recharge_to_db(self) -> int:
        """
        Sync nightly recharge data from API to database.

        Returns:
            Number of recharge records synced
        """
        recharge_data = self.get_nightly_recharge()
        session = get_session()
        count = 0

        try:
            for recharge in recharge_data:
                recharge_date_str = recharge.get('date')
                if not recharge_date_str:
                    continue

                recharge_date = date_parser.parse(recharge_date_str).date()

                # Check if already exists
                existing = session.query(NightlyRecharge).filter_by(
                    user_id=self.user_id,
                    recharge_date=recharge_date
                ).first()

                if existing:
                    # Update existing record
                    existing.nightly_recharge_status = recharge.get('nightly_recharge_status')
                    existing.ans_charge = recharge.get('ans_charge')
                    existing.hrv_avg = recharge.get('hrv', {}).get('avg')
                    existing.hrv_rmssd = recharge.get('hrv', {}).get('rmssd')
                    existing.breathing_rate_avg = recharge.get('breathing_rate_avg')
                    existing.heart_rate_avg = recharge.get('heart_rate_avg')
                    existing.raw_payload = recharge
                else:
                    record = NightlyRecharge(
                        user_id=self.user_id,
                        recharge_date=recharge_date,
                        nightly_recharge_status=recharge.get('nightly_recharge_status'),
                        ans_charge=recharge.get('ans_charge'),
                        hrv_avg=recharge.get('hrv', {}).get('avg'),
                        hrv_rmssd=recharge.get('hrv', {}).get('rmssd'),
                        breathing_rate_avg=recharge.get('breathing_rate_avg'),
                        heart_rate_avg=recharge.get('heart_rate_avg'),
                        raw_payload=recharge,
                        source='api'
                    )
                    session.add(record)
                    count += 1

            session.commit()
            logger.info(f"Synced {count} nightly recharge records from API")

        except Exception as e:
            session.rollback()
            logger.error(f"Error syncing nightly recharge: {e}")
            raise
        finally:
            session.close()

        return count

    def sync_all(self) -> Dict[str, int]:
        """
        Sync all data types from API to database.

        Returns:
            Dictionary with counts for each data type
        """
        init_db()  # Ensure tables exist

        return {
            'exercises': self.sync_exercises_to_db(),
            'sleep': self.sync_sleep_to_db(),
            'nightly_recharge': self.sync_nightly_recharge_to_db()
        }
