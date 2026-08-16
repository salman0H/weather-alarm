import urllib.request, json, urllib.error
request = urllib.request.Request(
    "https://api.groq.com/openai/v1/chat/completions",
    data=json.dumps({"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "hi"}]}).encode("utf-8"),
    headers={"Authorization": "Bearer invalid", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    method="POST"
)
try:
    urllib.request.urlopen(request)
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode())
