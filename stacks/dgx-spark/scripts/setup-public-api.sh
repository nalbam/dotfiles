#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

key_path="$HOME/.config/spark-secret-key"
[[ -f "$key_path" && "$(stat -c %a "$key_path")" == 600 ]] || {
  echo "A mode 0600 key file is required at $key_path." >&2
  exit 1
}
python3 -B - "$key_path" <<'PY'
import re
import sys
from pathlib import Path

key = Path(sys.argv[1]).read_bytes()
if not re.fullmatch(rb"[A-Za-z0-9_+/=-]{32,128}\n?", key):
    raise SystemExit("The API key must be 32-128 base64/hex characters with at most one trailing newline.")
PY

[[ -f .env ]] || { echo "Deploy Spark before enabling the public API." >&2; exit 1; }
mode="$(sed -n 's/^SPARK_MODE=//p' .env | tail -1)"
[[ "$mode" == models || "$mode" == flash ]] || {
  echo "The public API requires models or flash mode." >&2
  exit 1
}

python3 -B scripts/services.py write-targets "$mode"
docker compose --profile public config --quiet
docker compose --profile public pull api-gateway
docker compose --profile public run --rm --no-deps --entrypoint /bin/sh api-gateway -ec \
  'export MODEL_API_KEY="$(cat /run/secrets/model_api_key)"; exec caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile'
docker compose --profile public up -d --force-recreate api-gateway

python3 -B - "$key_path" <<'PY'
import sys
import urllib.error
import urllib.request
from pathlib import Path

url = "http://127.0.0.1:18000"
key = Path(sys.argv[1]).read_text().rstrip("\n")
blocked = (
    ("/v1/models", {}),
    ("/v1/models", {"Authorization": "Bearer invalid-key"}),
    ("/invocations", {}),
    ("/metrics", {"Authorization": f"Bearer {key}"}),
)
for path, headers in blocked:
    request = urllib.request.Request(url + path, headers=headers)
    try:
        urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as error:
        if error.code != 401:
            raise SystemExit(f"Expected 401 for {path}, got {error.code}") from error
    else:
        raise SystemExit(f"Blocked request succeeded: {path}")

request = urllib.request.Request(url + "/v1/models", headers={"Authorization": f"Bearer {key}"})
with urllib.request.urlopen(request, timeout=10) as response:
    if response.status != 200:
        raise SystemExit(f"Authenticated request returned {response.status}")
print("API gateway authentication: OK")
PY

tailscale funnel --bg --https=8443 http://127.0.0.1:18000
tailscale funnel status
