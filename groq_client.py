"""
Groq LLM Client — Zero-Dependency (standard urllib only).

Responsibility:
    Translate a raw OWM alert description into a concise, public-friendly Persian
    message suitable for Telegram dispatch.
    Uses temperature=0.0 for deterministic, reproducible output.
    Injects the live statistical probability into the system prompt so the LLM
    always quotes the exact figure extracted from the OpenWeatherMap hourly data.
"""

import json
import sys
import urllib.error
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
    'You MUST explicitly include the following exact statistical probability at the end of your message: '
    '"Probability of occurrence: {probability}%" (translate this phrase to Persian naturally). '
    "Be deterministic and precise."
)

# Returned when the LLM call fails (network error, auth failure, rate limit, etc.)
# This ensures the pipeline always dispatches something rather than crashing.
FALLBACK_SUMMARY = (
    "⚠️ <i>AI summary unavailable — displaying raw alert description below.</i>"
)


def summarize_description(api_key, description, probability=0, timeout=15):
    """
    Calls the Groq Chat Completions API to produce a concise Persian alert summary.

    If the API key is missing, invalid, or the service is temporarily unreachable,
    the function logs the error to stderr and returns FALLBACK_SUMMARY instead of
    raising an exception. This prevents a single LLM failure from aborting the
    entire alert dispatch pipeline.

    Args:
        api_key (str): Groq API key. If empty or a placeholder, the call is skipped.
        description (str): Raw OWM alert description to summarize.
        probability (int): Probability of precipitation (0–100) to inject into the prompt.
        timeout (int): HTTP socket timeout in seconds.

    Returns:
        str: Persian summary string with HTML formatting, or FALLBACK_SUMMARY on error.
    """
    # Skip the network call entirely when running in test mode or with a placeholder key
    if not api_key or api_key in ("TEST_MODE_PLACEHOLDER", "x"):
        return (
            f"[TEST MODE] Alert summary skipped — no real Groq key provided. "
            f"Probability of occurrence: {probability}%."
        )

    formatted_prompt = SYSTEM_PROMPT.format(probability=probability)

    body = {
        "model": MODEL,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": description},
        ],
    }

    request = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        print(
            f"[Groq] HTTP {e.code} {e.reason} — LLM summary skipped; "
            "using fallback text. Check GROQ_API_KEY validity and account quota.",
            file=sys.stderr,
        )
        return FALLBACK_SUMMARY
    except urllib.error.URLError as e:
        print(f"[Groq] Network error — {e.reason}. Using fallback text.", file=sys.stderr)
        return FALLBACK_SUMMARY
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"[Groq] Unexpected response structure — {e}. Using fallback text.", file=sys.stderr)
        return FALLBACK_SUMMARY
    except Exception as e:
        print(f"[Groq] Unexpected error — {e}. Using fallback text.", file=sys.stderr)
        return FALLBACK_SUMMARY
