"""
Weather API integration for Health Digest.

Uses OpenWeatherMap API for historical weather data at exercise locations.
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional, List

import requests

from .config import Config

logger = logging.getLogger(__name__)


class WeatherAPIError(Exception):
    """Custom exception for Weather API errors."""
    pass


class WeatherAPI:
    """
    Client for OpenWeatherMap API.

    Used to fetch historical weather data for exercise timestamps.
    """

    BASE_URL = "https://api.openweathermap.org/data/3.0/onecall/timemachine"
    CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
    FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

    def __init__(self, api_key: str = None):
        """
        Initialize Weather API client.

        Args:
            api_key: OpenWeatherMap API key (defaults to config)
        """
        self.api_key = api_key or getattr(Config, 'OPENWEATHERMAP_API_KEY', '')

    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    def get_historical_weather(
        self,
        lat: float,
        lon: float,
        timestamp: datetime
    ) -> Optional[Dict]:
        """
        Get historical weather data for a specific location and time.

        Args:
            lat: Latitude
            lon: Longitude
            timestamp: Datetime of the exercise

        Returns:
            Weather data dictionary or None if failed
        """
        if not self.is_configured():
            logger.warning("OpenWeatherMap API key not configured")
            return None

        try:
            unix_timestamp = int(timestamp.timestamp())

            response = requests.get(
                self.BASE_URL,
                params={
                    "lat": lat,
                    "lon": lon,
                    "dt": unix_timestamp,
                    "appid": self.api_key,
                    "units": "metric"
                },
                timeout=10
            )

            if response.status_code == 401:
                raise WeatherAPIError("Invalid API key")
            elif response.status_code == 429:
                raise WeatherAPIError("Rate limit exceeded")
            elif response.status_code != 200:
                logger.warning(f"Weather API error: {response.status_code}")
                return None

            data = response.json()

            # Extract relevant data from response
            if "data" in data and len(data["data"]) > 0:
                weather_data = data["data"][0]
                return {
                    "temp_c": weather_data.get("temp"),
                    "feels_like_c": weather_data.get("feels_like"),
                    "humidity": weather_data.get("humidity"),
                    "wind_speed": weather_data.get("wind_speed"),
                    "wind_deg": weather_data.get("wind_deg"),
                    "pressure": weather_data.get("pressure"),
                    "clouds": weather_data.get("clouds"),
                    "conditions": (weather_data.get("weather", [{}])[0].get("main", "Unknown")
                                   if weather_data.get("weather") else "Unknown"),
                    "description": (weather_data.get("weather", [{}])[0].get("description", "")
                                    if weather_data.get("weather") else ""),
                    "uvi": weather_data.get("uvi"),
                    "timestamp": timestamp.isoformat()
                }

            return None

        except requests.RequestException as e:
            logger.error(f"Weather API request failed: {e}")
            return None
        except WeatherAPIError as e:
            logger.error(f"Weather API error: {e}")
            return None

    def get_current_weather(
        self,
        lat: float,
        lon: float
    ) -> Optional[Dict]:
        """
        Get current weather for a location.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Weather data dictionary or None if failed
        """
        if not self.is_configured():
            return None

        try:
            response = requests.get(
                self.CURRENT_URL,
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "metric"
                },
                timeout=10
            )

            if response.status_code != 200:
                return None

            data = response.json()

            return {
                "temp_c": data.get("main", {}).get("temp"),
                "feels_like_c": data.get("main", {}).get("feels_like"),
                "humidity": data.get("main", {}).get("humidity"),
                "wind_speed": data.get("wind", {}).get("speed"),
                "conditions": (data.get("weather", [{}])[0].get("main", "Unknown")
                               if data.get("weather") else "Unknown"),
                "description": (data.get("weather", [{}])[0].get("description", "")
                                if data.get("weather") else "")
            }

        except requests.RequestException as e:
            logger.error(f"Current weather request failed: {e}")
            return None

    def get_forecast(
        self,
        lat: float,
        lon: float,
        days: int = 5
    ) -> Optional[List[Dict]]:
        """
        Get weather forecast for a location.

        Args:
            lat: Latitude
            lon: Longitude
            days: Number of days to forecast (max 5)

        Returns:
            List of forecast data or None if failed
        """
        if not self.is_configured():
            return None

        try:
            response = requests.get(
                self.FORECAST_URL,
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "metric",
                    "cnt": days * 8  # 3-hour intervals
                },
                timeout=10
            )

            if response.status_code != 200:
                return None

            data = response.json()
            forecasts = []

            for item in data.get("list", []):
                forecasts.append({
                    "dt": item.get("dt"),
                    "dt_txt": item.get("dt_txt"),
                    "temp_c": item.get("main", {}).get("temp"),
                    "humidity": item.get("main", {}).get("humidity"),
                    "wind_speed": item.get("wind", {}).get("speed"),
                    "conditions": (item.get("weather", [{}])[0].get("main", "Unknown")
                                   if item.get("weather") else "Unknown")
                })

            return forecasts

        except requests.RequestException as e:
            logger.error(f"Forecast request failed: {e}")
            return None

    def find_optimal_days(
        self,
        lat: float,
        lon: float,
        optimal_temp_range: tuple = (10, 15)
    ) -> List[Dict]:
        """
        Find optimal training days in the forecast.

        Args:
            lat: Latitude
            lon: Longitude
            optimal_temp_range: Tuple of (min_temp, max_temp)

        Returns:
            List of optimal days with weather data
        """
        forecast = self.get_forecast(lat, lon)
        if not forecast:
            return []

        optimal_days = []
        min_temp, max_temp = optimal_temp_range

        # Group by date and find midday readings
        by_date = defaultdict(list)

        for item in forecast:
            dt_txt = item.get("dt_txt", "")
            if dt_txt:
                date_str = dt_txt.split(" ")[0]
                by_date[date_str].append(item)

        for date_str, items in by_date.items():
            # Find midday reading (around 12:00)
            midday = next((i for i in items if "12:00" in i.get("dt_txt", "")), items[0])
            temp = midday.get("temp_c", 0)

            if min_temp <= temp <= max_temp:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    optimal_days.append({
                        "date": date_str,
                        "day_name": date_obj.strftime("%A"),
                        "temp_c": temp,
                        "conditions": midday.get("conditions", "Unknown"),
                        "is_optimal": True
                    })
                except ValueError:
                    pass

        return optimal_days


def enrich_exercises_with_weather(exercises: List, weather_api: WeatherAPI = None) -> List[Dict]:
    """
    Enrich exercises with weather data.

    Args:
        exercises: List of Exercise objects
        weather_api: WeatherAPI instance (creates new if not provided)

    Returns:
        List of dicts with exercise and weather data
    """
    if weather_api is None:
        weather_api = WeatherAPI()

    if not weather_api.is_configured():
        logger.info("Weather API not configured - skipping weather enrichment")
        return [{"exercise": ex, "weather": None} for ex in exercises]

    enriched = []

    for ex in exercises:
        weather = None

        # Try to get location from raw payload (would contain GPS route)
        if ex.raw_payload:
            route = ex.raw_payload.get("route", [])
            if route and len(route) > 0:
                first_point = route[0]
                lat = first_point.get("latitude")
                lon = first_point.get("longitude")

                if lat and lon and ex.start_time:
                    weather = weather_api.get_historical_weather(lat, lon, ex.start_time)

        enriched.append({
            "exercise": ex,
            "weather": weather
        })

    return enriched
