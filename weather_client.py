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

    Includes: current, hourly, daily, alerts.
    Excludes: minutely (high-volume, not needed for alert logic).
    Uses metric units so temperatures are Celsius and wind speed is m/s.

    Args:
        lat (float): Latitude of the zone center.
        lon (float): Longitude of the zone center.
        api_key (str): OpenWeatherMap API key.
        timeout (int): Socket timeout in seconds.

    Returns:
        dict: Raw OWM payload, or an empty dict on network/auth/parse failure.
    """
    # In TEST_MODE, serve the local fixture instead of hitting the live API
    if os.environ.get("TEST_MODE", "false").lower() == "true":
        return _load_fixture()

    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "exclude": "minutely",   # Keep current, hourly, daily, alerts
        "units": "metric",       # Celsius temperatures; wind in m/s
        "lang": "fa",
    }
    url = f"{OWM_BASE_URL}?{urllib.parse.urlencode(params)}"

    request = urllib.request.Request(url, headers={"User-Agent": "weather-alert-bot/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload
    except urllib.error.HTTPError as e:
        print(f"[OWM] HTTP {e.code} {e.reason} — lat={lat} lon={lon}", file=sys.stderr)
        return {}
    except urllib.error.URLError as e:
        print(f"[OWM] Network error — {e.reason} — lat={lat} lon={lon}", file=sys.stderr)
        return {}
    except json.JSONDecodeError as e:
        print(f"[OWM] JSON parse error — {e} — lat={lat} lon={lon}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"[OWM] Unexpected error — {e} — lat={lat} lon={lon}", file=sys.stderr)
        return {}


def _load_fixture():
    """
    Returns the local mock fixture payload used in TEST_MODE.
    Logs a warning if the fixture file cannot be read.

    Returns:
        dict: Mock payload, or {} if unreadable.
    """
    try:
        with open(MOCK_FIXTURE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[OWM] Fixture not found: {MOCK_FIXTURE_PATH}", file=sys.stderr)
        return {}
    except json.JSONDecodeError as e:
        print(f"[OWM] Fixture JSON error: {e}", file=sys.stderr)
        return {}

def fetch_waqi_data(token, timeout=10):
    """
    Fetches the real-time Air Quality Index (AQI) from the WAQI API for Mashhad.

    Args:
        token (str): WAQI API token.
        timeout (int): Socket timeout in seconds.

    Returns:
        dict: A simplified dictionary with 'aqi' and 'dominant' pollutant.
              Returns a safe default (e.g., {'aqi': -1, 'dominant': 'unknown'}) on failure.
    """
    if os.environ.get("TEST_MODE", "false").lower() == "true":
        return {"aqi": 85, "dominant": "pm25"}

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
            }
        else:
            print(f"[WAQI] API returned non-ok status: {payload.get('data')}", file=sys.stderr)
            return fallback
    except urllib.error.HTTPError as e:
        print(f"[WAQI] HTTP {e.code} {e.reason}", file=sys.stderr)
        return fallback
    except urllib.error.URLError as e:
        print(f"[WAQI] Network error — {e.reason}", file=sys.stderr)
        return fallback
    except json.JSONDecodeError as e:
        print(f"[WAQI] JSON parse error — {e}", file=sys.stderr)
        return fallback
    except Exception as e:
        print(f"[WAQI] Unexpected error — {e}", file=sys.stderr)
        return fallback

