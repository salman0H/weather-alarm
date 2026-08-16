"""
Entry point Workflow B: telegram-listener.yml

Responsibility: Listens to incoming Telegram updates (messages and callbacks).
1. Registers new subscribers upon receiving a message.
2. Handles /setphone to save phone numbers for future SMS features.
3. Checks for callback_query from InlineKeyboardMarkup buttons.
   If the callback data (MD5 hash) matches the pending alert, it acks it.
"""

import os
import re
import sys

import state as state_module
import telegram_client

PHONE_PATTERN = re.compile(r"^/setphone\s+(\+?\d{10,14})$")


def handle_update(update, current_state, log):
    # Handle callback queries from InlineKeyboardMarkup
    if "callback_query" in update:
        callback = update["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        data = callback.get("data", "")
        
        subscriber = state_module.get_subscriber(current_state, chat_id)
        active = subscriber.get("active_alert")
        
        if active and active["status"] == "PENDING_ACK" and active["alert_id"] == data:
            active["status"] = "ACKED"
            log(f"[{chat_id}] Alert acknowledged via callback: {active['event']}")
        return

    # Handle standard messages
    message = update.get("message")
    if not message or "text" not in message:
        return

    chat_id = message["chat"]["id"]
    text = message["text"].strip()
    subscriber = state_module.get_subscriber(current_state, chat_id)

    phone_match = PHONE_PATTERN.match(text)
    if phone_match:
        subscriber["phone_number"] = phone_match.group(1)
        log(f"[{chat_id}] Phone number registered")
        return

    # Fallback to /ok command for ack
    if text == "/ok":
        active = subscriber.get("active_alert")
        if active and active["status"] == "PENDING_ACK":
            active["status"] = "ACKED"
            log(f"[{chat_id}] Alert acknowledged via /ok: {active['event']}")
        return


def main():
    telegram_token = os.environ["TELEGRAM_BOT_TOKEN"]

    def log(msg):
        print(msg, file=sys.stderr)

    current_state = state_module.load_state()
    updates = telegram_client.get_updates(telegram_token, offset=current_state["offset"] + 1)

    for update in updates:
        handle_update(update, current_state, log)
        current_state["offset"] = max(current_state["offset"], update["update_id"])

    state_module.save_state(current_state)
    log(f"{len(updates)} updates processed")


if __name__ == "__main__":
    main()
