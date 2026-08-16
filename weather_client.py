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


def fetch_alerts_for_zone(lat, lon, api_key, timeout=10):
    """
    Fetches the alerts array from OpenWeatherMap for a specific coordinate.
    If no alerts are active, the 'alerts' key will not exist in the response ->
    in that case, an empty list is returned.

    We use exclude=current,minutely,hourly,daily to reduce payload size and
    focus only on alerts.
    """
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "exclude": "current,minutely,hourly,daily",
        "lang": "fa"
    }
    url = f"{OWM_BASE_URL}?{urllib.parse.urlencode(params)}"

    request = urllib.request.Request(url, headers={"User-Agent": "weather-alert-bot/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return payload.get("alerts", [])


def fetch_alerts_mocked(fixture_path):
    """
    Test mode: Returns the content of the fixture file instead of calling the actual API.
    The fixture structure matches the real OpenWeatherMap response, so the rest
    of the pipeline (dedupe, message generation, dispatch) works identically
    with mocked data.
    """
    with open(fixture_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("alerts", [])


def is_mock_mode():
    return os.environ.get("MOCK_ALERT", "false").lower() == "true"
