"""
End-to-end integration test for the alert pipeline using TEST_MODE mock fixture.

Validates the complete subscriber state machine without requiring real API keys:
    1. One unique alert is loaded from the fixture via TEST_MODE.
    2. First check: state transitions NO_ALERT -> PENDING_ACK; message dispatched.
    3. Immediate re-check: RESEND_INTERVAL not elapsed; no second dispatch.
    4. Simulate /ok acknowledgment: state transitions to ACKED.
    5. Post-ACKED check: same alert already ACKED; no re-dispatch.
    6. CLEAR_SKIES check: triggers the daily brief via LLM instead of alerts.

Run:
    TEST_MODE=true AUTHORIZED_USER_ID=999 \\
    TELEGRAM_BOT_TOKEN=x GROQ_API_KEY=x \\
    python tests/test_pipeline.py
"""

import os
import sys

# Ensure the project root is on sys.path when running directly from this file
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

os.environ["TEST_MODE"] = "true"  # Activate fixture loading in weather_client.py

import weather_alert_check as wac   # noqa: E402
import state as state_module         # noqa: E402
import telegram_client               # noqa: E402
import groq_client                   # noqa: E402

SENT_ALERTS = []
SENT_BRIEFS = []


def fake_send_alert(telegram_token, groq_api_key, chat_id, alert, phone_number=None, aqi=-1, dominant_pollutant="unknown"):
    """Monkeypatch replacement for wac.send_alert_dispatch"""
    SENT_ALERTS.append((chat_id, alert["event"]))
    return f"[mock alert message for {alert['event']}]"


def fake_send_message(telegram_token, chat_id, message, reply_markup=None):
    """Monkeypatch replacement for telegram_client.send_message (used by brief)"""
    SENT_BRIEFS.append(message)
    return "[mock brief message]"


def fake_generate_daily_brief(api_key, analytics_json, timeout=15):
    """Monkeypatch replacement for groq_client.generate_daily_brief"""
    return "Mocked Persian AI Brief"


def run():
    """
    Executes the state machine test and asserts correctness at each step.
    Raises AssertionError with a descriptive message if any phase fails.
    """
    # Monkeypatch to prevent network calls
    wac.send_alert_dispatch = fake_send_alert
    telegram_client.send_message = fake_send_message
    groq_client.generate_daily_brief = fake_generate_daily_brief

    fresh_state = {
        "offset": 0,
        "subscribers": {"999": {"phone_number": None, "active_alert": None}},
    }

    current_alerts, metrics, hourly_data, tz_offset, dynamic_zone_profiles = wac.collect_alerts_across_zones("unused", "unused")
    assert len(current_alerts) >= 1, (
        f"Expected at least one alert from fixture; got {len(current_alerts)}. "
        "Check tests/fixtures/sample_alert.json."
    )
    print(f"[Test] Loaded {len(current_alerts)} alert(s). Metrics: MaxPop={metrics['max_pop']} MaxWind={metrics['max_wind']}")

    # Phase 1: First check — initial dispatch expected
    wac.route_and_dispatch(fresh_state, "999", current_alerts, metrics, hourly_data, tz_offset, dynamic_zone_profiles, "tok", "key", print)
    assert fresh_state["subscribers"]["999"]["active_alert"]["status"] == "PENDING_ACK", (
        "After first check, subscriber status must be PENDING_ACK."
    )
    assert len(SENT_ALERTS) == 1, "Exactly one alert message must be dispatched on first check."
    print("PASS Phase 1: Initial alert dispatch succeeded.")

    # Phase 2: Immediate re-check — resend interval not elapsed; no dispatch
    wac.route_and_dispatch(fresh_state, "999", current_alerts, metrics, hourly_data, tz_offset, dynamic_zone_profiles, "tok", "key", print)
    assert len(SENT_ALERTS) == 1, (
        "No resend should occur before RESEND_INTERVAL_MINUTES has elapsed."
    )
    print("PASS Phase 2: No premature alert resend.")

    # Phase 3: Simulate /ok acknowledgment
    fresh_state["subscribers"]["999"]["active_alert"]["status"] = "ACKED"
    print("PASS Phase 3: Acknowledgment simulated (/ok).")

    # Phase 4: Post-ACKED check — same alert still present but ACKED; no re-dispatch
    wac.route_and_dispatch(fresh_state, "999", current_alerts, metrics, hourly_data, tz_offset, dynamic_zone_profiles, "tok", "key", print)
    assert len(SENT_ALERTS) == 1, (
        "After ACKED, the same alert must not be re-dispatched."
    )
    print("PASS Phase 4: No re-dispatch after acknowledgment.")

    # Phase 5: CLEAR_SKIES transition
    print("\n--- Testing CLEAR_SKIES Route ---")
    SENT_ALERTS.clear()
    SENT_BRIEFS.clear()
    
    # Simulate calm conditions with no alerts
    metrics["max_wind"] = 10.0
    metrics["max_pop"] = 0.50
    metrics["aqi"] = 85
    
    wac.route_and_dispatch(fresh_state, "999", {}, metrics, hourly_data, tz_offset, dynamic_zone_profiles, "tok", "key", print)
    assert len(SENT_ALERTS) == 0, "No alerts should be sent in CLEAR_SKIES."
    assert len(SENT_BRIEFS) == 1, "Exactly one daily brief should be dispatched."
    assert fresh_state["subscribers"]["999"]["active_alert"]["status"] == "EXPIRED", (
        "Previous active alert should be marked EXPIRED upon clearing."
    )
    print("PASS Phase 5: CLEAR_SKIES path correctly routed to daily brief.")
    
    # Phase 6: High AQI Predictive Warning
    print("\n--- Testing High AQI Risk Engine ---")
    SENT_ALERTS.clear()
    SENT_BRIEFS.clear()
    metrics["aqi"] = 160
    
    wac.route_and_dispatch(fresh_state, "999", {}, metrics, hourly_data, tz_offset, dynamic_zone_profiles, "tok", "key", print)
    assert len(SENT_ALERTS) == 1, "High AQI should trigger a predictive warning alert."
    assert "Predictive Warning" in SENT_ALERTS[0][1], "Event should be Predictive Warning."
    print("PASS Phase 6: High AQI successfully triggered predictive warning.")

    print("\nAll pipeline tests passed successfully.")


if __name__ == "__main__":
    run()
