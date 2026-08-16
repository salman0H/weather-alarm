"""
Groq LLM Client — Zero-Dependency (standard urllib only).

Responsibility:
    Produce concise, public-friendly Persian messages suitable for Telegram dispatch.
    Uses temperature=0.0 for deterministic, reproducible output.
"""

import json
import sys
import urllib.error
import urllib.request

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

ALERT_SYSTEM_PROMPT = (
    "You are a strict meteorological data-to-text parser summarizing official weather alerts. "
    "Output must be strictly in Persian. "
    "Rewrite the official alert description into a maximum of two simple, public-friendly sentences. "
    "Do not add any safety recommendations—only explain what is happening. "
    "You MUST NOT invent, estimate, or hallucinate any weather metrics. "
    "Use ONLY the numerical data provided in the user message. If a metric is absent, omit it entirely. "
    "Format the output using simple HTML tags (like <b> or <i>) if emphasis is needed, "
    "but strictly avoid using any Markdown formatting (no asterisks, no hash headers). "
    'You MUST explicitly include the following exact statistical probability at the end of your message: '
    '"Probability of occurrence: {probability}%" (translate this phrase to Persian naturally). '
    "Be deterministic and precise."
)

BRIEF_SYSTEM_PROMPT = (
    "You are a strict data-to-text parser generating a daily intelligence brief. "
    "Output must be strictly in Persian. "
    "You MUST ONLY use the exact numerical values provided for each time period. "
    "Do not infer trends beyond what the numbers directly show. "
    "Format using Telegram HTML tags (<b>, <i>, <code>). "
    "Use visual dividers, relevant emojis (🌤️, 📉, 💨), and clear hierarchical sections "
    "like '📅 Today\\'s Intelligence Brief', '🕒 Chronological Forecast', '📍 Zone Analysis'."
)

# Returned when the LLM call fails (network error, auth failure, rate limit, etc.)
FALLBACK_SUMMARY = (
    "⚠️ <i>AI summary unavailable — displaying raw alert description below.</i>"
)


def _call_groq(api_key, system_prompt, user_content, timeout=15):
    if not api_key or api_key in ("TEST_MODE_PLACEHOLDER", "x"):
        return f"[TEST MODE] AI summary skipped — no real Groq key provided. User content: {user_content}"

    body = {
        "model": MODEL,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    }

    request = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "UrbanWeatherIntelligence/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            error_body = "Could not read error body."
        print(f"[Groq] HTTP {e.code} {e.reason} — LLM summary skipped. Details: {error_body}", file=sys.stderr)
        return FALLBACK_SUMMARY
    except urllib.error.URLError as e:
        print(f"[Groq] Network error — {e.reason}.", file=sys.stderr)
        return FALLBACK_SUMMARY
    except Exception as e:
        print(f"[Groq] Unexpected error — {e}.", file=sys.stderr)
        return FALLBACK_SUMMARY


def generate_alert_message(api_key, description, probability=0, timeout=15):
    """
    Calls the Groq Chat Completions API to produce a concise Persian alert summary.
    """
    formatted_prompt = ALERT_SYSTEM_PROMPT.format(probability=probability)
    return _call_groq(api_key, formatted_prompt, description, timeout)


def generate_daily_brief(api_key, analytics_json, timeout=15):
    """
    Generates a daily brief in Persian given the chronological metrics.
    """
    return _call_groq(api_key, BRIEF_SYSTEM_PROMPT, analytics_json, timeout)
