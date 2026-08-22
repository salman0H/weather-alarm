"""
Telegram Bot API Client — Zero-Dependency.

Responsibilities:
  - send_message: For Workflow A (Sending alerts)
  - get_updates: For Workflow B (Receiving user ack callbacks/messages)
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

TELEGRAM_BASE_URL = "https://api.telegram.org/bot{token}/{method}"
TELEGRAM_MAX_LENGTH = 4096


def _split_message(text, max_length=TELEGRAM_MAX_LENGTH):
    """
    Splits a long message into multiple parts, each under max_length characters.

    Strategy (in priority order):
      1. If text fits in one message — return as-is.
      2. Try to split at section dividers (────) so each part contains
         a complete, self-contained section.
      3. Fall back to splitting at blank lines (paragraph boundaries).
      4. Hard-split at max_length as a last resort.

    This guarantees related content (e.g., 'Zone Analysis') is never
    split mid-section across two messages.
    """
    if len(text) <= max_length:
        return [text]

    parts = []

    # Try splitting on section-divider lines (e.g. ────────────────────)
    # We keep the divider with the PRECEDING section.
    divider_pattern = "\n────"

    def _try_split(source, delimiter):
        chunks = source.split(delimiter)
        result = []
        current = ""
        for i, chunk in enumerate(chunks):
            # Re-attach the delimiter we split on (except before the first chunk)
            segment = (delimiter + chunk) if i > 0 else chunk
            if len(current) + len(segment) <= max_length:
                current += segment
            else:
                if current:
                    result.append(current.strip())
                current = segment
        if current:
            result.append(current.strip())
        return result

    segments = _try_split(text, divider_pattern)

    # If any segment is still too long, further split on blank lines
    for seg in segments:
        if len(seg) <= max_length:
            parts.append(seg)
        else:
            sub_parts = _try_split(seg, "\n\n")
            for sp in sub_parts:
                if len(sp) <= max_length:
                    parts.append(sp)
                else:
                    # Hard-split as last resort
                    for i in range(0, len(sp), max_length):
                        parts.append(sp[i:i + max_length])

    return [p for p in parts if p.strip()]


def _call(token, method, params, timeout=10):
    url = TELEGRAM_BASE_URL.format(token=token, method=method)
    
    # We must send JSON if we have complex structures like reply_markup
    data = json.dumps(params).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"[Telegram HTTP Error] Code {e.code}: {error_body}", file=sys.stderr)
        result = json.loads(error_body)
        if not result.get("ok"):
            sys.exit(f"[FATAL] Telegram API rejected the request: {error_body}")
        return result
    except Exception as e:
        sys.exit(f"[FATAL] Unexpected error in Telegram API call: {e}")


def send_message(token, chat_id, text, parse_mode="HTML", reply_markup=None):
    """
    Sends a text message to a specific chat_id.
    If the message exceeds Telegram's 4096-character limit, it is automatically
    split into multiple logical parts (split at section dividers, then blank lines).
    The reply_markup (inline keyboard) is only attached to the last part so
    the Acknowledge button appears exactly once.
    """
    parts = _split_message(text)

    last_result = None
    for i, part in enumerate(parts):
        is_last = (i == len(parts) - 1)
        params = {
            "chat_id": chat_id,
            "text": part,
            "parse_mode": parse_mode
        }
        if is_last and reply_markup:
            params["reply_markup"] = reply_markup

        last_result = _call(token, "sendMessage", params)

    return last_result


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
