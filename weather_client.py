"""
OpenWeatherMap One Call API v3.0 Client — Zero-Dependency (standard urllib only).

Responsibility:
    Fetch the full weather payload for a geographical point.
    Field extraction and alert logic are handled in weather_alert_check.py.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

OWM_BASE_URL = "https://api.openweathermap.org/data/3.0/onecall"

MOCK_FIXTURE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "tests", "fixtures", "sample_alert.json"
)


def fetch_weather_data_for_zone(lat, lon, api_key, timeout=10):
    """
    Fetches the full OWM One Call v3 payload for a single lat/lon point.

    Args:
        lat (float): Latitude of the zone center.
        lon (float): Longitude of the zone center.
        api_key (str): OpenWeatherMap API key.
        timeout (int): Socket timeout in seconds.

    Returns:
        tuple: (dict payload, str status_code)
    """
    if os.environ.get("TEST_MODE", "false").lower() == "true":
        return _load_fixture(), "200"

    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "exclude": "minutely",
        "units": "metric",
        "lang": "fa",
    }
    url = f"{OWM_BASE_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "weather-alert-bot/1.0"})
    
    fallback = {
        "current": {"temp": 20.0, "humidity": 30, "wind_speed": 5.0, "uvi": 5.0},
        "hourly": [{"dt": 0, "temp": 20.0, "pop": 0.0, "wind_speed": 5.0, "uvi": 5.0} for _ in range(24)],
        "alerts": []
    }

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload, str(response.getcode())
    except urllib.error.HTTPError as e:
        print(f"[OWM] HTTP {e.code} {e.reason} — lat={lat} lon={lon}", file=sys.stderr)
        return fallback, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        print(f"[OWM] Network error — {e.reason} — lat={lat} lon={lon}", file=sys.stderr)
        return fallback, "Network Error"
    except Exception as e:
        print(f"[OWM] Unexpected error — {e} — lat={lat} lon={lon}", file=sys.stderr)
        return fallback, "Error"


def _load_fixture():
    try:
        with open(MOCK_FIXTURE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[OWM] Fixture error: {e}", file=sys.stderr)
        return {}


def fetch_waqi_data(token, timeout=10):
    """
    Fetches the real-time Air Quality Index (AQI) from the WAQI API for Mashhad.

    Returns:
        tuple: (dict payload, str status_code)
    """
    if os.environ.get("TEST_MODE", "false").lower() == "true":
        return {"aqi": 85, "dominant": "pm25"}, "200"

    url = f"https://api.waqi.info/feed/mashhad/?token={token}"
    request = urllib.request.Request(url, headers={"User-Agent": "weather-alert-bot/1.0"})
    
    fallback = {"aqi": -1, "dominant": "unknown"}

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        
        if payload.get("status") == "ok":
            data = payload.get("data", {})
            return {
                "aqi": data.get("aqi", -1),
                "dominant": data.get("dominentpol", "unknown")
            }, "200"
        else:
            return fallback, "WAQI Status Error"
    except urllib.error.HTTPError as e:
        return fallback, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return fallback, "Network Error"
    except Exception as e:
        return fallback, "Error"

