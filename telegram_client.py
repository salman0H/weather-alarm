"""
Telegram Bot API Client — Zero-Dependency.

Responsibilities:
  - send_message: For Workflow A (Sending alerts)
  - get_updates: For Workflow B (Receiving user ack callbacks/messages)
"""

import json
import urllib.error
import urllib.parse
import urllib.request

TELEGRAM_BASE_URL = "https://api.telegram.org/bot{token}/{method}"


def _call(token, method, params, timeout=10):
    url = TELEGRAM_BASE_URL.format(token=token, method=method)
    
    # We must send JSON if we have complex structures like reply_markup
    data = json.dumps(params).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Telegram error response has JSON body (e.g. chat not found) ->
        # return it to allow caller to log it instead of crashing.
        return json.loads(e.read().decode("utf-8"))


def send_message(token, chat_id, text, parse_mode="HTML", reply_markup=None):
    """
    Sends a text message to a specific chat_id.
    Can include inline keyboards via reply_markup for alert acknowledgment.
    """
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        params["reply_markup"] = reply_markup
        
    return _call(token, "sendMessage", params)


def send_location(token, chat_id, latitude, longitude):
    """
    Sends location as a separate message so the user can see the center 
    of the affected zone on the Telegram map directly.
    """
    return _call(token, "sendLocation", {
        "chat_id": chat_id,
        "latitude": latitude,
        "longitude": longitude
    })


def get_updates(token, offset=0, timeout=0):
    """
    Fetches new updates (messages, callbacks) from the given offset.
    offset must be the last processed update_id + 1 so Telegram clears it.
    """
    result = _call(token, "getUpdates", {
        "offset": offset,
        "timeout": timeout
    })
    if not result.get("ok"):
        return []
    return result.get("result", [])
