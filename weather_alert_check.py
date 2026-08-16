"""
Entry point Workflow A: weather-alert-check.yml

Execution steps:
  1. Load config/zones.json
  2. Data Collection (Fetch from OWM or Mock)
  3. Analysis & State Machine Routing
     - ALERT: active official alerts
     - PREDICTIVE_WARNING: no alerts, but high risk thresholds
     - CLEAR_SKIES: calm conditions
  4. Generate and Dispatch message via Telegram
  5. Save state.json and update HTML dashboard
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from enum import Enum

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

ZONE_PROFILES = {
    "مرکز شهر": "Central urban area, high heat retention, dense traffic.",
    "وکیل‌آباد": "Western district, higher elevation, more prone to strong winds.",
    "طرق": "Southern outskirts, open terrain, faster temperature drops at night.",
    "قاسم‌آباد": "North-western residential zone, moderate exposure.",
    "الهیه / طلاب": "Eastern residential zone, mixed density.",
    "شهرک صنعتی توس": "Industrial zone in the northwest, high pollution potential.",
    "حرم مطهر": "Central religious hub, extremely high foot traffic.",
    "کوهسنگی": "South-western park area near mountains, localized cooling.",
    "هاشمیه": "South-western affluent area, elevated terrain.",
    "احمدآباد": "Central-west commercial hub."
}

class PipelineState(Enum):
    ALERT = 1
    PREDICTIVE_WARNING = 2
    CLEAR_SKIES = 3

def load_zones():
    with open(ZONES_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def alert_id_for(alert):
    raw = f"{alert.get('event')}|{alert.get('start')}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def compute_day_part_analytics(hourly_data, timezone_offset_secs):
    """
    Buckets hourly slots into Morning (06-12), Afternoon (12-18), and Evening (18-24).
    Uses local time (UTC + offset).
    """
    buckets = {
        "Morning": {"temps": [], "pops": [], "winds": [], "uvis": []},
        "Afternoon": {"temps": [], "pops": [], "winds": [], "uvis": []},
        "Evening": {"temps": [], "pops": [], "winds": [], "uvis": []}
    }
    
    for hour in hourly_data[:24]:
        dt = datetime.fromtimestamp(hour.get("dt", 0) + timezone_offset_secs, tz=timezone.utc)
        hour_num = dt.hour
        
        bucket = None
        if 6 <= hour_num < 12:
            bucket = "Morning"
        elif 12 <= hour_num < 18:
            bucket = "Afternoon"
        elif 18 <= hour_num <= 23:
            bucket = "Evening"
            
        if bucket:
            buckets[bucket]["temps"].append(hour.get("temp", 0))
            buckets[bucket]["pops"].append(hour.get("pop", 0) * 100)
            buckets[bucket]["winds"].append(hour.get("wind_speed", 0))
            buckets[bucket]["uvis"].append(hour.get("uvi", 0))
            
    analytics = {}
    for name, data in buckets.items():
        if data["temps"]:
            analytics[name] = {
                "avg_temp": round(sum(data["temps"]) / len(data["temps"]), 1),
                "peak_temp": round(max(data["temps"]), 1),
                "avg_pop": round(sum(data["pops"]) / len(data["pops"]), 1),
                "peak_pop": round(max(data["pops"]), 1),
                "avg_wind": round(sum(data["winds"]) / len(data["winds"]), 1),
                "peak_wind": round(max(data["winds"]), 1),
                "avg_uvi": round(sum(data["uvis"]) / len(data["uvis"]), 1)
            }
        else:
            analytics[name] = None
    
    return analytics

def collect_alerts_across_zones(owm_api_key):
    merged = {}
    global_metrics = {
        "max_pop": 0.0,
        "max_wind": 0.0,
        "max_uvi": 0.0,
        "max_temp": -99.0,
        "current_temp_avg": 0.0,
        "current_hum_avg": 0.0,
        "zones_count": 0
    }
    
    total_temp = 0
    total_hum = 0
    all_hourly_data = []
    tz_offset = 0

    for zone in load_zones():
        payload = weather_client.fetch_weather_data_for_zone(zone["lat"], zone["lon"], owm_api_key)
        
        if not tz_offset:
            tz_offset = payload.get("timezone_offset", 12600)
            
        raw_alerts = payload.get("alerts", [])
        hourly_data = payload.get("hourly", [])
        if not all_hourly_data and hourly_data:
            all_hourly_data = hourly_data
            
        current_data = payload.get("current", {})
        
        temp = current_data.get("temp", 0)
        hum = current_data.get("humidity", 0)
        wind = current_data.get("wind_speed", 0)
        uvi = current_data.get("uvi", 0)
        
        total_temp += temp
        total_hum += hum
        global_metrics["zones_count"] += 1
        global_metrics["max_wind"] = max(global_metrics["max_wind"], wind)
        global_metrics["max_uvi"] = max(global_metrics["max_uvi"], uvi)
        global_metrics["max_temp"] = max(global_metrics["max_temp"], temp)
        
        max_pop = 0.0
        if hourly_data:
            next_24_hours = hourly_data[:24]
            max_pop = max((hour.get("pop", 0) for hour in next_24_hours), default=0.0)
            
        global_metrics["max_pop"] = max(global_metrics["max_pop"], max_pop)
            
        for alert in raw_alerts:
            aid = alert_id_for(alert)
            if aid not in merged:
                merged[aid] = {
                    "alert_id": aid,
                    "event": alert.get("event"),
                    "description": alert.get("description"),
                    "start": alert.get("start"),
                    "end": alert.get("end"),
                    "zones": [],
                    "max_pop": max_pop
                }
            if zone["zone"] not in merged[aid]["zones"]:
                merged[aid]["zones"].append(zone["zone"])
            if max_pop > merged[aid]["max_pop"]:
                merged[aid]["max_pop"] = max_pop

    if global_metrics["zones_count"] > 0:
        global_metrics["current_temp_avg"] = total_temp / global_metrics["zones_count"]
        global_metrics["current_hum_avg"] = total_hum / global_metrics["zones_count"]

    return merged, global_metrics, all_hourly_data, tz_offset

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
        f"🚨 <b>WEATHER ALERT — {event}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📍 <b>Affected Zones:</b> {zones_text}\n"
        f"⏱ <b>Active:</b> {format_time(start)} – {format_time(end)}\n"
        f"📊 <b>Risk Level:</b> <code>{level} — {level_info['label']}</code>\n\n"
        f"<i>{summary}</i>\n\n"
        f"💡 <b>Safety Guidance</b>\n{tips_text}\n\n"
        f"<i>Tap ✅ Acknowledge to dismiss.</i>"
    )

def dispatch_sms(phone_number, message):
    if phone_number:
        pass

def send_alert_dispatch(telegram_token, groq_api_key, chat_id, alert, phone_number=None):
    level = severity.classify_severity(alert["event"])
    level_info = severity.SEVERITY_LEVELS[level]
    
    prob_percentage = int(alert.get("max_pop", 0) * 100)
    
    summary = groq_client.generate_alert_message(
        api_key=groq_api_key,
        description=alert["description"],
        probability=prob_percentage
    )

    message = build_alert_message(
        level_info, level, alert["event"], summary,
        alert["zones"], alert["start"], alert["end"]
    )
    
    if phone_number:
        dispatch_sms(phone_number, f"Weather Alert: {alert['event']} - {level}. Check Telegram for details.")

    coords = zone_coords(alert["zones"][0]) if alert.get("zones") else None
    if coords:
        telegram_client.send_location(telegram_token, chat_id, coords[0], coords[1])

    reply_markup = {
        "inline_keyboard": [
            [{"text": "✅ Acknowledge", "callback_data": alert["alert_id"]}]
        ]
    }

    telegram_client.send_message(telegram_token, chat_id, message, reply_markup=reply_markup)
    return message

def route_and_dispatch(current_state, authorized_user_id, current_alerts, global_metrics, hourly_data, tz_offset, telegram_token, groq_api_key, log):
    """
    Guarantees a single Telegram dispatch based on strict State Machine routing.
    """
    state_enum = PipelineState.CLEAR_SKIES
    
    # Analysis & State determination
    if current_alerts:
        state_enum = PipelineState.ALERT
    elif global_metrics["max_wind"] > 15 or global_metrics["max_pop"] > 0.70:
        state_enum = PipelineState.PREDICTIVE_WARNING

    subscriber = state_module.get_subscriber(current_state, authorized_user_id)
    phone_number = subscriber.get("phone_number")
    active = subscriber.get("active_alert")

    if state_enum in (PipelineState.ALERT, PipelineState.PREDICTIVE_WARNING):
        # We handle predictive warning as an alert payload
        if state_enum == PipelineState.PREDICTIVE_WARNING:
            now_ts = int(datetime.now(timezone.utc).timestamp())
            alert_payload = {
                "event": "Predictive Warning",
                "start": now_ts,
                "end": now_ts + (4 * 3600),
                "description": f"Predictive Engine detected high risk conditions: Wind {global_metrics['max_wind']}m/s, Precipitation Prob {global_metrics['max_pop']*100}%.",
                "max_pop": global_metrics["max_pop"],
                "zones": ["All Mashhad Zones"]
            }
            alert_payload["alert_id"] = alert_id_for(alert_payload)
            current_alerts = {alert_payload["alert_id"]: alert_payload}

        first_alert = next(iter(current_alerts.values()))

        should_send_new = False
        
        if active is None:
            should_send_new = True
        elif active["status"] == "PENDING_ACK":
            if active["alert_id"] not in current_alerts:
                active["status"] = "EXPIRED"
                log(f"[{authorized_user_id}] Alert expired: {active['event']}")
                should_send_new = True
            else:
                # Existing active alert
                if minutes_since(active["last_sent_at"]) >= RESEND_INTERVAL_MINUTES:
                    send_alert_dispatch(telegram_token, groq_api_key, authorized_user_id, active, phone_number)
                    active["last_sent_at"] = now_iso()
                    active["resend_count"] += 1
                    log(f"[{authorized_user_id}] Resend #{active['resend_count']} for: {active['event']}")
        else: # ACKED or EXPIRED
            if first_alert["alert_id"] != active.get("alert_id"):
                should_send_new = True

        if should_send_new:
            send_alert_dispatch(telegram_token, groq_api_key, authorized_user_id, first_alert, phone_number)
            subscriber["active_alert"] = {
                **first_alert,
                "first_sent_at": now_iso(),
                "last_sent_at": now_iso(),
                "resend_count": 0,
                "status": "PENDING_ACK"
            }
            log(f"[{authorized_user_id}] New alert sent: {first_alert['event']}")
    
    else:  # CLEAR_SKIES
        if active and active["status"] != "EXPIRED":
             active["status"] = "EXPIRED"
             
        day_part_analytics = compute_day_part_analytics(hourly_data, tz_offset)
        
        prompt_data = {
            "analytics": day_part_analytics,
            "zone_context": ZONE_PROFILES
        }
        
        summary = groq_client.generate_daily_brief(groq_api_key, json.dumps(prompt_data, ensure_ascii=False))
        
        telegram_client.send_message(telegram_token, authorized_user_id, summary)
        log(f"[{authorized_user_id}] Clear Skies daily brief dispatched via LLM.")


def main():
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    owm_api_key = os.environ.get("OWM_API_KEY", "")
    groq_api_key = os.environ.get("GROQ_API_KEY")
    authorized_user_id = os.environ.get("AUTHORIZED_USER_ID")
    test_mode = os.environ.get("TEST_MODE", "false").lower() == "true"

    def log(msg):
        print(msg, file=sys.stderr)

    if test_mode:
        log("[Pipeline] TEST_MODE=true — loading local fixture; relaxing API key guards.")
        owm_api_key = owm_api_key or "TEST_MODE_PLACEHOLDER"
        groq_api_key = groq_api_key or "TEST_MODE_PLACEHOLDER"
    else:
        if not telegram_token or not groq_api_key or not owm_api_key:
            log("[Pipeline] ERROR — Missing required credentials: "
                "TELEGRAM_BOT_TOKEN / OWM_API_KEY / GROQ_API_KEY. Exiting.")
            sys.exit(1)

    if not authorized_user_id:
        log("[Pipeline] ERROR — AUTHORIZED_USER_ID is not set. Exiting for security.")
        sys.exit(1)

    if not telegram_token:
        log("[Pipeline] ERROR — TELEGRAM_BOT_TOKEN is not set. Exiting.")
        sys.exit(1)

    # 1. Data Collection & Extraction
    current_alerts, global_metrics, hourly_data, tz_offset = collect_alerts_across_zones(owm_api_key)
    log(
        f"[Pipeline] Active alerts: {len(current_alerts)} | "
        f"MaxWind={global_metrics['max_wind']:.1f}m/s "
        f"MaxPoP={global_metrics['max_pop'] * 100:.0f}% "
        f"AvgTemp={global_metrics['current_temp_avg']:.1f}°C"
    )

    current_state = state_module.load_state()

    # 2. State Machine Routing & Dispatch
    route_and_dispatch(
        current_state, authorized_user_id, current_alerts, global_metrics, 
        hourly_data, tz_offset, telegram_token, groq_api_key, log
    )

    state_module.save_state(current_state)

    # 3. HTML Update
    report_path = visualize_alert.render_report(load_zones(), current_alerts, global_metrics)
    log(f"[Pipeline] HTML dashboard updated at {report_path}")

if __name__ == "__main__":
    main()
