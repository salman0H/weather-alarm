"""
Groq API Client — Zero-Dependency.

Responsibility: Fetch raw alert data (event, description, zones) and convert it 
into a clear, urgent Persian message suitable for Telegram dispatch.
Uses a low temperature for deterministic output.
"""

import json
import urllib.request

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are an assistant summarizing official weather alerts. "
    "Output must be strictly in Persian. "
    "Rewrite the official alert description into a maximum of two simple, public-friendly sentences. "
    "Do not add any safety recommendations—only explain what is happening. "
    "Format the output using simple HTML tags (like <b> or <i>) if emphasis is needed, "
    "but strictly avoid using any Markdown formatting (no asterisks, no hash headers). "
    "Be deterministic and precise."
)


def summarize_description(api_key, description, timeout=15):
    """
    Summarizes the official alert description into simple language.
    Safety tips and the final message structure are built deterministically 
    in weather_alert_check.py (not via LLM) to prevent hallucinated advice.
    """
    body = {
        "model": MODEL,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": description}
        ]
    }

    request = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return payload["choices"][0]["message"]["content"].strip()
