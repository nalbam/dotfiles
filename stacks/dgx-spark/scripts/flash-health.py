"""Check the Flash scheduler by generating a short answer through its API."""

import json
import urllib.request


request = urllib.request.Request(
    "http://127.0.0.1:8000/v1/chat/completions",
    data=json.dumps({"model": "qwen3.8-flash-next", "messages": [{"role": "user", "content": "Reply with OK."}],
                     "chat_template_kwargs": {"enable_thinking": False}, "max_tokens": 16, "temperature": 0}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(request, timeout=20) as response:
    result = json.load(response)
if not result["choices"][0]["message"].get("content", "").strip():
    raise SystemExit("Flash generation returned no answer")
