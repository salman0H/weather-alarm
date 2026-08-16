"""
End-to-end integration test for the alert pipeline using TEST_MODE mock fixture.

Validates the complete subscriber state machine without requiring real API keys:
    1. One unique alert is loaded from the fixture via TEST_MODE.
    2. First check: state transitions NO_ALERT -> PENDING_ACK; message dispatched.
    3. Immediate re-check: RESEND_INTERVAL not elapsed; no second dispatch.
    4. Simulate /ok acknowledgment: state transitions to ACKED.
    5. Post-ACKED check: same alert already ACKED; no re-dispatch.

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

SENT_MESSAGES = []


def fake_send_alert(telegram_token, groq_api_key, chat_id, alert, phone_number=None):
    """
    Monkeypatch replacement for wac.send_alert.
    Records dispatches without making real Groq or Telegram API calls.
    """
    SENT_MESSAGES.append((chat_id, alert["event"]))
    return f"[mock message for {alert['event']}]"


def run():
    """
    Executes the four-phase state machine test and asserts correctness at each step.
    Raises AssertionError with a descriptive message if any phase fails.
    """
    # Monkeypatch to prevent network calls
    wac.send_alert = fake_send_alert

    fresh_state = {
        "offset": 0,
        "subscribers": {"999": {"phone_number": None, "active_alert": None}},
    }

    # collect_alerts_across_zones now returns a 2-tuple: (merged_alerts, global_metrics)
    current_alerts, metrics = wac.collect_alerts_across_zones(owm_api_key="unused-in-test-mode")
    assert len(current_alerts) >= 1, (
        f"Expected at least one alert from fixture; got {len(current_alerts)}. "
        "Check tests/fixtures/sample_alert.json."
    )
    print(f"[Test] Loaded {len(current_alerts)} alert(s). Metrics: {metrics}")

    subscriber = fresh_state["subscribers"]["999"]

    # Phase 1: First check — initial dispatch expected
    wac.process_subscriber(subscriber, current_alerts, "tok", "key", "999", print)
    assert subscriber["active_alert"]["status"] == "PENDING_ACK", (
        "After first check, subscriber status must be PENDING_ACK."
    )
    assert len(SENT_MESSAGES) == 1, "Exactly one message must be dispatched on first check."
    print("PASS Phase 1: Initial dispatch succeeded.")

    # Phase 2: Immediate re-check — resend interval not elapsed; no dispatch
    wac.process_subscriber(subscriber, current_alerts, "tok", "key", "999", print)
    assert len(SENT_MESSAGES) == 1, (
        "No resend should occur before RESEND_INTERVAL_MINUTES has elapsed."
    )
    print("PASS Phase 2: No premature resend.")

    # Phase 3: Simulate /ok acknowledgment
    subscriber["active_alert"]["status"] = "ACKED"
    print("PASS Phase 3: Acknowledgment simulated (/ok).")

    # Phase 4: Post-ACKED check — same alert still present but ACKED; no re-dispatch
    wac.process_subscriber(subscriber, current_alerts, "tok", "key", "999", print)
    assert len(SENT_MESSAGES) == 1, (
        "After ACKED, the same alert must not be re-dispatched."
    )
    print("PASS Phase 4: No re-dispatch after acknowledgment.")

    print("\nAll pipeline tests passed successfully.")


if __name__ == "__main__":
    run()
