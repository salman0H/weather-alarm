"""
Groq LLM Client — Zero-Dependency (standard urllib only).

Responsibility:
    Produce concise, public-friendly Persian messages suitable for Telegram dispatch.
    Uses temperature=0.0 for deterministic, reproducible output.
"""

import json
import re
import sys
import urllib.error
import urllib.request

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

ALERT_SYSTEM_PROMPT = (
    "You are an elite meteorological AI. Analyze the provided dynamic data array. "
    "Do NOT output robotic, repetitive lists. Synthesize the zone data into a fluid, highly accurate Persian intelligence briefing. "
    "Group zones with similar conditions together to create a readable, human-like narrative. Highlight extremes and anomalies. "
    "Output must be strictly in Persian. "
    "If specific data fields are missing, DO NOT print 'Not available' or 'Unknown'. "
    "Instead, dynamically adjust the UI layout to completely hide/remove those sections. "
    "The final message must always look premium, complete, and perfectly formatted. "
    "You MUST explicitly include an 'Air Quality Report' section in the output if AQI data is provided. "
    "Use appropriate emojis for air quality (e.g., 😷 for high AQI, 🍃 for good AQI, 🌫️ for moderate). "
    "You MUST NOT invent, estimate, or hallucinate any weather metrics. "
    "Use ONLY the numerical data provided in the user message. If a metric is absent, omit it entirely. "
    "Format the output using simple HTML tags (like <b> or <i>) if emphasis is needed, "
    "but strictly avoid using any Markdown formatting (no asterisks, no hash headers). "
    'You MUST explicitly include the following exact statistical probability at the end of your message: '
    '"Probability of occurrence: {probability}%" (translate this phrase to Persian naturally). '
    "Be deterministic and precise."
)

BRIEF_SYSTEM_PROMPT = (
    "You are an elite meteorological AI. Analyze the provided dynamic data array. "
    "Do NOT output robotic, repetitive lists. Synthesize the zone data into a fluid, highly accurate Persian intelligence briefing. "
    "Group zones with similar conditions together to create a readable, human-like narrative. Highlight extremes and anomalies. "
    "Output must be strictly in Persian. "
    "If specific data fields are missing, DO NOT print 'Not available' or 'Unknown'. "
    "Instead, dynamically adjust the UI layout to completely hide/remove those sections. "
    "The final message must always look premium, complete, and perfectly formatted. "
    "You MUST explicitly include an 'Air Quality Report' section in the output if AQI data is provided. "
    "Use appropriate emojis for air quality (e.g., 😷 for high AQI, 🍃 for good AQI, 🌫️ for moderate). "
    "You MUST ONLY use the exact numerical values provided for each time period. "
    "Do not infer trends beyond what the numbers directly show. "
    "Format using Telegram HTML tags (<b>, <i>, <code>). "
    "Use visual dividers, relevant emojis (🌤️, 📉, 💨), and clear hierarchical sections "
    "like '📅 Today\\'s Intelligence Brief', '🕒 Chronological Forecast', '📍 Zone Analysis', and '🌬️ Air Quality Report'."
)

# Returned when the LLM call fails (network error, auth failure, rate limit, etc.)
FALLBACK_SUMMARY = (
    "⚠️ <i>AI summary unavailable — displaying raw alert description below.</i>"
)


def clean_typography(text):
    if not text:
        return text

    # Strip both closed <think>...</think> and unclosed <think>... blocks
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'<think>.*', '', text, flags=re.DOTALL)
    text = text.strip()

    # Repair broken HTML: close any unclosed common formatting tags
    for tag in ['b', 'i', 'code', 'u', 's']:
        open_count = text.count(f'<{tag}>')
        close_count = text.count(f'</{tag}>')
        if open_count > close_count:
            text = text.rstrip() + f'</{tag}>' * (open_count - close_count)
    
    return text


def _call_groq(api_key, system_prompt, user_content, timeout=15):
    if not api_key or api_key in ("TEST_MODE_PLACEHOLDER", "x"):
        return f"[TEST MODE] AI summary skipped — no real Groq key provided. User content: {user_content}"

    body = {
        "model": MODEL,
        "temperature": 0.0,
        "max_tokens": 1024,
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
            choice = payload.get("choices", [])[0]
            finish_reason = choice.get("finish_reason", "unknown")
            content = choice.get("message", {}).get("content", "")
            
            print(f"[Groq API] finish_reason={finish_reason}, content_length={len(content)}", file=sys.stderr)
            if finish_reason == "length":
                print("[Groq Warning] Response was truncated! Increase max_tokens.", file=sys.stderr)
                
            return clean_typography(content)
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


def generate_alert_message(api_key, description, probability=0, is_degraded_mode=False, timeout=15):
    """
    Calls the Groq Chat Completions API to produce a concise Persian alert summary.
    """
    formatted_prompt = ALERT_SYSTEM_PROMPT.format(probability=probability)
    if is_degraded_mode:
        formatted_prompt += "\n\nIf 'is_degraded_mode' is True, intelligently insert a beautiful, polite system notice at the top of the message explaining that the dashboard is currently operating on cached/fallback data due to upstream sensor maintenance."
        description = f"is_degraded_mode=True\n\n{description}"
        
    return _call_groq(api_key, formatted_prompt, description, timeout)


def generate_daily_brief(api_key, analytics_json, is_degraded_mode=False, timeout=15):
    """
    Generates a daily brief in Persian given the chronological metrics.
    """
    formatted_prompt = BRIEF_SYSTEM_PROMPT
    if is_degraded_mode:
        formatted_prompt += "\n\nIf 'is_degraded_mode' is True, intelligently insert a beautiful, polite system notice at the top of the message explaining that the dashboard is currently operating on cached/fallback data due to upstream sensor maintenance."
        analytics_json = f"is_degraded_mode=True\n\n{analytics_json}"
        
    return _call_groq(api_key, formatted_prompt, analytics_json, timeout)
