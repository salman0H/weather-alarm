"""
Persistent State Management Layer.

The main architecture is Stateless (e.g., GitHub Actions runs on a fresh VM
that is destroyed afterwards). To support the "alert until acknowledged" feature,
we need persistent storage across runs.
Solution: A state.json file in the repository that each run reads, modifies, and commits.

state.json structure:

{
  "offset": 123456789,               # Last update_id processed by listener
  "subscribers": {
    "<chat_id>": {
      "phone_number": null,          # Future feature: Phone number for SMS
      "active_alert": null or {
        "alert_id": "md5 hash",
        "event": "...",
        "zones": ["Vakilabad", "Ghasemabad"],
        "description": "...",
        "start": 1755248400,
        "end": 1755262800,
        "first_sent_at": "ISO-8601",
        "last_sent_at": "ISO-8601",
        "resend_count": 0,
        "status": "PENDING_ACK"      # PENDING_ACK | ACKED | EXPIRED
      }
    }
  }
}
"""

import json
import os

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

DEFAULT_STATE = {
    "offset": 0,
    "subscribers": {}
}


def load_state():
    """
    Reads state.json. If the file does not exist (first run),
    returns a valid empty state to avoid null checks in the rest of the code.
    """
    if not os.path.exists(STATE_PATH):
        return json.loads(json.dumps(DEFAULT_STATE))

    with open(STATE_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            # Corrupted or empty file -> return empty state to prevent pipeline crash
            return json.loads(json.dumps(DEFAULT_STATE))

    data.setdefault("offset", 0)
    data.setdefault("subscribers", {})
    return data


def save_state(state):
    """
    Writes the state to disk in a human-readable format (indent=2, ensure_ascii=False).
    Committing the file is the responsibility of the workflow (git commit step),
    not this function.
    """
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def get_subscriber(state, chat_id):
    """
    Returns a subscriber record; if it's the first time, creates a default record.
    chat_id is always stored as a string in the dictionary because JSON keys
    must be strings.
    """
    key = str(chat_id)
    if key not in state["subscribers"]:
        state["subscribers"][key] = {
            "phone_number": None,
            "active_alert": None
        }
    return state["subscribers"][key]
