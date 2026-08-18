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

# We now use the standard Current Weather & 5-Day Forecast APIs for high reliability

MOCK_FIXTURE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "tests", "fixtures", "sample_alert.json"
)


def fetch_weather_data_for_zone(lat, lon, api_key, timeout=10):
    """
    Fetches weather data using the highly reliable Current Weather and Forecast APIs.
    Maps the response back to the One Call structure so the pipeline doesn't break.
    """
    if os.environ.get("TEST_MODE", "false").lower() == "true":
        return _load_fixture(), "200"

    headers = {"User-Agent": "weather-alert-bot/1.0"}
    fallback = {
        "current": {"temp": 20.0, "humidity": 30, "wind_speed": 5.0},
        "hourly": [{"dt": 0, "temp": 20.0, "humidity": 30, "pop": 0.0, "wind_speed": 5.0} for _ in range(24)],
        "alerts": []
    }

    current_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={api_key}&lang=fa"
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&units=metric&appid={api_key}&lang=fa"

    try:
        # 1. Fetch Current
        req_c = urllib.request.Request(current_url, headers=headers)
        with urllib.request.urlopen(req_c, timeout=timeout) as response:
            data_c = json.loads(response.read().decode("utf-8"))
            
        # 2. Fetch Forecast (3-hour intervals)
        req_f = urllib.request.Request(forecast_url, headers=headers)
        with urllib.request.urlopen(req_f, timeout=timeout) as response:
            data_f = json.loads(response.read().decode("utf-8"))

        # Map to pipeline format
        payload = {
            "timezone_offset": data_c.get("timezone", 12600),
            "current": {
                "temp": data_c["main"]["temp"],
                "humidity": data_c["main"]["humidity"],
                "wind_speed": data_c["wind"]["speed"],
            },
            "hourly": [],
            "alerts": [] # Standard APIs do not provide official alerts; relying on predictive engine
        }

        for item in data_f.get("list", []):
            payload["hourly"].append({
                "dt": item["dt"],
                "temp": item["main"]["temp"],
                "humidity": item["main"]["humidity"],
                "pop": item.get("pop", 0.0),
                "wind_speed": item["wind"]["speed"],
            })

        return payload, "200"
    except urllib.error.HTTPError as e:
        print(f"[OWM] HTTP {e.code} {e.reason} — lat={lat} lon={lon}", file=sys.stderr)
        return fallback, f"OWM HTTP {e.code} {e.reason}"
    except KeyError as e:
        print(f"[OWM] KeyError — {str(e)} — lat={lat} lon={lon}", file=sys.stderr)
        return fallback, f"OWM KeyError '{e.args[0]}'"
    except urllib.error.URLError as e:
        print(f"[OWM] Network error — {e.reason} — lat={lat} lon={lon}", file=sys.stderr)
        return fallback, f"OWM Network Error: {e.reason}"
    except Exception as e:
        print(f"[OWM] Unexpected error — {e} — lat={lat} lon={lon}", file=sys.stderr)
        return fallback, f"OWM Error: {str(e)}"


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

    url = f"https://api.waqi.info/feed/@11601/?token={token}"
    request = urllib.request.Request(url, headers={"User-Agent": "weather-alert-bot/1.0"})
    
    fallback = {"aqi": -1, "dominant": "unknown"}

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        
        if payload.get("status") == "ok":
            data = payload["data"]
            aqi = data["aqi"]
            iaqi = data.get("iaqi", {})
            return {
                "aqi": aqi,
                "dominant": data.get("dominentpol", "unknown"),
                "pm25": iaqi.get("pm25", {}).get("v", -1),
                "pm10": iaqi.get("pm10", {}).get("v", -1)
            }, "200"
        else:
            return fallback, f"WAQI Error: {payload.get('data', 'Unknown Status')}"
    except urllib.error.HTTPError as e:
        return fallback, f"WAQI HTTP {e.code} {e.reason}"
    except KeyError as e:
        return fallback, f"WAQI KeyError '{e.args[0]}'"
    except urllib.error.URLError as e:
        return fallback, f"WAQI Network Error: {e.reason}"
    except Exception as e:
        return fallback, f"WAQI Error: {str(e)}"

