"""
OpenWeatherMap One Call API Client — Zero-Dependency (standard urllib only).

Responsibility: Fetch raw alerts for a geographical point.
Merging and logic for detecting new alerts are handled in weather_alert_check.py.
"""

import json
import os
import urllib.parse
import urllib.request

OWM_BASE_URL = "https://api.openweathermap.org/data/3.0/onecall"


def fetch_weather_data_for_zone(lat, lon, api_key, timeout=10):
    """
    Fetches the full payload (excluding current and minutely) to access 
    both alerts and hourly probability of precipitation (pop).
    """
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "exclude": "current,minutely",
        "lang": "fa"
    }
    url = f"{OWM_BASE_URL}?{urllib.parse.urlencode(params)}"

    request = urllib.request.Request(url, headers={"User-Agent": "weather-alert-bot/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return payload


def is_mock_mode():
    """
    Strictly enforced real data for production. Mock mode is disabled.
    """
    return False

