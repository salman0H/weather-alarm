# Urban Weather Intelligence & Early Warning System - Technical Documentation

## Project Goal
To expand the existing Telegram bot (`salman0H/telegram-vibe-agent`) with a new feature: automatically fetching official weather alerts for different locations across Mashhad city, sending them to subscribed users, and resending them periodically until the user acknowledges (acks) the alert. It also features a localized "Mission Control Center" HTML dashboard.

## Why the Initial Architecture (Cron on GitHub Actions) Was Not Enough
Every execution of GitHub Actions runs on a fresh, stateless virtual machine that is destroyed at the end of the run. For a "resend until user ack" feature, two things missing in a purely stateless architecture are required:

1. Persistent memory that survives across different runs (the state of each alert, for each user).
2. A way to receive incoming messages/callbacks from the user (not just sending outputs).

**Solution:** A `state.json` file in the repository that each run reads and commits, plus a second workflow that independently polls Telegram's incoming updates.

## Architecture Components

| Component | Responsibility | Trigger |
|---|---|---|
| `weather_alert_check.py` (Workflow A) | Check alerts for 10 zones in Mashhad, send/resend alerts | Cron every 20 minutes |
| `telegram_listener.py` (Workflow B) | Receive incoming updates, record acks, record phone numbers | Cron every 2 minutes |
| `visualize_alert.py` | Generates the Mission Control UI HTML dashboard | Called by Workflow A |
| `state.json` | The only shared state between both workflows | Versioned file in repo |
| `weather_client.py` | Communication with OpenWeatherMap One Call | — |
| `groq_client.py` | Generation of deterministic Persian alert text | — |
| `telegram_client.py` | Sending messages and receiving updates from Telegram | — |

## Geographical Coverage (Multi-Zone)
Instead of a single point (City Center), `config/zones.json` now includes 10 strategic points spread across the city. Each execution of Workflow A loops over all points and merges identical alerts using an MD5 hash of `event + start` to ensure users are not flooded with duplicate alerts for storms affecting multiple zones simultaneously.

## Alert State Machine (Per User)

```
NO_ALERT --(new alert)--> PENDING_ACK
PENDING_ACK --(resend interval passed & not acked)--> PENDING_ACK (resend_count++)
PENDING_ACK --(user clicks Acknowledge inline button)--> ACKED
PENDING_ACK --(alert no longer in API)--> EXPIRED
ACKED / EXPIRED --(new alert appears)--> PENDING_ACK
```

## API Inputs/Outputs

### 1. OpenWeatherMap One Call — `weather_client.fetch_alerts_for_zone`
Input: `lat`, `lon`, `appid`, `exclude=current,minutely,hourly,daily`, `lang=fa`
Output (Relevant section):
```json
{
  "alerts": [
    {
      "sender_name": "string",
      "event": "string",
      "start": 1755248400,
      "end": 1755262800,
      "description": "string",
      "tags": ["Flood"]
    }
  ]
}
```
Full sample: `tests/fixtures/sample_alert.json`

### 2. Groq — `groq_client.summarize_description`
Input: `event`, `description`
Output: A deterministic, simple Persian string suitable for dispatch (formatted with HTML tags, no Markdown headers).

### 3. Telegram — `telegram_client`
`send_message(token, chat_id, text, reply_markup)` → Sends the message along with an Inline Keyboard containing the MD5 alert hash.
`get_updates(token, offset)` → Retrieves an array of updates including `callback_query` and `message` payloads.

## Mission Control UI
A highly modern, dark-mode Mission Control dashboard (`alert_report.html`) is generated dynamically by `visualize_alert.py`.
- Features: GSAP animations, a Leaflet interactive map with plotted zones, a dynamic Weather Risk Score, an AI Briefing panel, and an Active Alerts center.
- Generation: Can be executed manually via `MOCK_ALERT=true python3 visualize_alert.py`.

## Testing Without Real Alerts (Mock Mode)
Since real severe weather alerts are rare, end-to-end testing is done with the `MOCK_ALERT=true` environment variable, which bypasses the actual API calls and uses `tests/fixtures/sample_alert.json`.

Run UI generation test:
```bash
MOCK_ALERT=true python3 visualize_alert.py
```

## Future Feature — SMS Dispatch
A user's `phone_number` can be saved in `state.json` using the `/setphone 09xxxxxxxxx` command. A placeholder `dispatch_sms` function has been integrated into `weather_alert_check.py`. The proposed escalation layer: if `resend_count` passes a certain threshold and the user hasn't acknowledged, the message will also be sent via an SMS gateway (e.g., Kavenegar for Iranian numbers).

## Required Environment Variables (GitHub Secrets)
- `TELEGRAM_BOT_TOKEN`
- `OWM_API_KEY`
- `GROQ_API_KEY`
