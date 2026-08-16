"""
Entry point Workflow A: weather-alert-check.yml

Execution steps:
  1. Load config/zones.json
  2. For each zone, fetch alerts from OpenWeatherMap (or mock in tests)
  3. Dedupe and merge identical alerts across different zones
  4. For each subscriber in state.json:
       - If no active_alert and a new alert exists -> initial send
       - If active_alert exists, is still in the current list, is PENDING_ACK,
         and RESEND_INTERVAL_MINUTES has passed -> resend
       - If active_alert exists but is no longer in the current list -> EXPIRED
  5. Save state.json (commit is handled by the next step of the workflow)
"""

import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone

import groq_client
import severity
import state as state_module
import telegram_client
import visualize_alert
import weather_client

RESEND_INTERVAL_MINUTES = 20
ZONES_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "zones.json")
MOCK_FIXTURE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "tests", "fixtures", "sample_alert.json"
)


def load_zones():
    import json
    with open(ZONES_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def alert_id_for(alert):
    """
    Unique key for each alert: MD5 hash of event + start.
    This key is used for deduplication across zones and to detect
    whether an alert is the "same as before" or a fresh one.
    """
    raw = f"{alert.get('event')}|{alert.get('start')}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def collect_alerts_across_zones(owm_api_key):
    """
    Loops over all zones and merges alerts based on alert_id.
    Returns: dict mapping alert_id -> {event, description, start, end, sender_name, zones: [...]}
    """
    merged = {}
    mock = weather_client.is_mock_mode()

    for zone in load_zones():
        if mock:
            raw_alerts = weather_client.fetch_alerts_mocked(MOCK_FIXTURE_PATH)
        else:
            raw_alerts = weather_client.fetch_alerts_for_zone(zone["lat"], zone["lon"], owm_api_key)

        for alert in raw_alerts:
            aid = alert_id_for(alert)
            if aid not in merged:
                merged[aid] = {
                    "alert_id": aid,
                    "event": alert.get("event"),
                    "description": alert.get("description"),
                    "start": alert.get("start"),
                    "end": alert.get("end"),
                    "zones": []
                }
            if zone["zone"] not in merged[aid]["zones"]:
                merged[aid]["zones"].append(zone["zone"])

        # In mock mode, we only need to process one zone's fixture to get the alerts
        if mock:
            break

    return merged


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def minutes_since(iso_timestamp):
    then = datetime.fromisoformat(iso_timestamp)
    return (datetime.now(timezone.utc) - then).total_seconds() / 60


def zone_coords(zone_name):
    for zone in load_zones():
        if zone["zone"] == zone_name:
            return zone["lat"], zone["lon"]
    return None


def format_time(unix_ts):
    if not unix_ts:
        return "Unknown"
    dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def build_alert_message(level_info, level, event, summary, zones_list, start, end):
    zones_text = ", ".join(zones_list)
    tips = severity.get_safety_tips(level)
    tips_text = "\n".join(f"• {tip}" for tip in tips)
    return (
        f"{level_info['emoji']} <b>{event}</b>\n"
        f"Severity: {level} — {level_info['label']}\n\n"
        f"Affected Zones: {zones_text}\n"
        f"Start: {format_time(start)}\n"
        f"End: {format_time(end)}\n\n"
        f"{summary}\n\n"
        f"<b>Safety Tips:</b>\n{tips_text}\n\n"
        f"<i>Please acknowledge below to stop receiving this alert.</i>"
    )


def dispatch_sms(phone_number, message):
    """
    Placeholder hook for future SMS gateway integration.
    This will be called if the subscriber has a phone number registered.
    """
    if phone_number:
        # TODO: Implement SMS API call here
        pass


def send_alert(telegram_token, groq_api_key, chat_id, alert, phone_number=None):
    level = severity.classify_severity(alert["event"])
    level_info = severity.SEVERITY_LEVELS[level]
    summary = groq_client.summarize_description(groq_api_key, alert["description"])

    message = build_alert_message(
        level_info, level, alert["event"], summary,
        alert["zones"], alert["start"], alert["end"]
    )
    
    if phone_number:
        dispatch_sms(phone_number, f"Weather Alert: {alert['event']} - {level}. Check Telegram for details.")

    # Send location separately to show the epicenter on the map
    coords = zone_coords(alert["zones"][0]) if alert.get("zones") else None
    if coords:
        telegram_client.send_location(telegram_token, chat_id, coords[0], coords[1])

    # Inline Keyboard for acknowledgment
    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ Acknowledge", "callback_data": alert["alert_id"]}]
        ]
    }

    telegram_client.send_message(telegram_token, chat_id, message, reply_markup=reply_markup)
    return message


def process_subscriber(subscriber, current_alerts, telegram_token, groq_api_key, chat_id, log):
    active = subscriber.get("active_alert")
    phone_number = subscriber.get("phone_number")

    if active is None:
        # No active alert -> if there's a new alert, send for the first time
        if current_alerts:
            # Simplification: If multiple alerts exist, prioritize the first one.
            first_alert = next(iter(current_alerts.values()))
            send_alert(telegram_token, groq_api_key, chat_id, first_alert, phone_number)
            subscriber["active_alert"] = {
                **first_alert,
                "first_sent_at": now_iso(),
                "last_sent_at": now_iso(),
                "resend_count": 0,
                "status": "PENDING_ACK"
            }
            log(f"[{chat_id}] New alert sent: {first_alert['event']}")
        return

    # Subscriber already has an active_alert
    if active["status"] != "PENDING_ACK":
        # ACKED or EXPIRED -> If another alert is active, start a new cycle
        if active["alert_id"] not in current_alerts and current_alerts:
            first_alert = next(iter(current_alerts.values()))
            send_alert(telegram_token, groq_api_key, chat_id, first_alert, phone_number)
            subscriber["active_alert"] = {
                **first_alert,
                "first_sent_at": now_iso(),
                "last_sent_at": now_iso(),
                "resend_count": 0,
                "status": "PENDING_ACK"
            }
            log(f"[{chat_id}] New alert (next cycle) sent: {first_alert['event']}")
        return

    # status == PENDING_ACK
    if active["alert_id"] not in current_alerts:
        # Alert is no longer present in official source -> stop resending
        active["status"] = "EXPIRED"
        log(f"[{chat_id}] Alert expired: {active['event']}")
        return

    if minutes_since(active["last_sent_at"]) >= RESEND_INTERVAL_MINUTES:
        send_alert(telegram_token, groq_api_key, chat_id, active, phone_number)
        active["last_sent_at"] = now_iso()
        active["resend_count"] += 1
        log(f"[{chat_id}] Resend #{active['resend_count']} for: {active['event']}")


def main():
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    owm_api_key = os.environ.get("OWM_API_KEY", "")
    groq_api_key = os.environ.get("GROQ_API_KEY")

    def log(msg):
        print(msg, file=sys.stderr)

    if not telegram_token or not groq_api_key:
        log("Missing required API keys. Exiting.")
        sys.exit(1)

    current_alerts = collect_alerts_across_zones(owm_api_key)
    log(f"Unique active alerts count: {len(current_alerts)}")

    current_state = state_module.load_state()

    for chat_id, subscriber in current_state["subscribers"].items():
        process_subscriber(subscriber, current_alerts, telegram_token, groq_api_key, chat_id, log)

    state_module.save_state(current_state)

    report_path = visualize_alert.render_report(load_zones(), current_alerts)
    log(f"Visual report generated at {report_path}")


if __name__ == "__main__":
    main()
