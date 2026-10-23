#!/usr/bin/env bash

set -euo pipefail
# Runs on DGX OS (Bash 5); empty arrays under set -u need Bash 4.4 or newer.
(( BASH_VERSINFO[0] * 100 + BASH_VERSINFO[1] >= 404 )) || { echo "${0##*/} needs Bash 4.4 or newer." >&2; exit 1; }

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

SPARK_MODE="${SPARK_MODE:-models}"
[[ "$SPARK_MODE" == comfyui || "$SPARK_MODE" == models || "$SPARK_MODE" == flash ]] || { echo "SPARK_MODE must be comfyui, models or flash" >&2; exit 1; }

failed=false
wait_seconds="${HEALTH_WAIT_SECONDS:-0}"
[[ "$wait_seconds" =~ ^[0-9]+$ ]] || { echo "HEALTH_WAIT_SECONDS must be a non-negative integer" >&2; exit 1; }
metrics_file="$(mktemp)"
system_stats_file="$(mktemp)"
trap 'rm -f -- "$metrics_file" "$system_stats_file"' EXIT

services=()
active_services="$(scripts/compose.sh config --services)"
while IFS= read -r service; do
  [[ -z "$service" ]] || services+=("$service")
done <<< "$active_services"
for service in "${services[@]}"; do
  deadline=$((SECONDS + wait_seconds))
  while true; do
    container_id="$(scripts/compose.sh service ps "$service" -q)"
    if [[ -n "$container_id" ]]; then
      state="$(docker inspect --format '{{.State.Status}}' "$container_id")"
      health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")"
      if [[ "$state" == running && ("$health" == healthy || "$health" == none) ]]; then
        break
      fi
    else
      state=absent
      health=none
    fi
    (( SECONDS >= deadline )) && break
    sleep 2
  done
  if [[ "$state" != running || ("$health" != healthy && "$health" != none) ]]; then
    echo "FAIL dgx-spark/$service: state=$state health=$health" >&2
    failed=true
  else
    echo "OK   dgx-spark/$service: state=$state health=$health"
  fi
done

if [[ "$SPARK_MODE" == comfyui ]]; then
  if curl -fsS --max-time 10 --output "$system_stats_file" http://127.0.0.1:8188/system_stats &&
    python3 -c 'import json,sys; data=json.load(open(sys.argv[1])); assert any("cuda" in str(device.get("type", "")).lower() for device in data.get("devices", []))' "$system_stats_file"; then
    echo "OK   ComfyUI :8188 API and CUDA device"
  else
    echo "FAIL ComfyUI :8188 API or CUDA device" >&2
    failed=true
  fi
fi

model_target_count=0
if [[ "$SPARK_MODE" == models || "$SPARK_MODE" == flash ]]; then
  probes="$(python3 -B scripts/services.py probes "$SPARK_MODE")"
  while IFS=$'\t' read -r service url; do
    [[ -n "$service" ]] || continue
    model_target_count=$((model_target_count + 1))
    if curl -fsS --max-time 10 --output "$metrics_file" "$url" &&
      grep -Eq '^[a-zA-Z_:][a-zA-Z0-9_:]*(\{|[[:space:]])' "$metrics_file"; then
      echo "OK   $service metrics"
    else
      echo "FAIL $service metrics" >&2
      failed=true
    fi
  done <<< "$probes"
fi

if [[ -s .env.grafana ]]; then
  alloy_ready=false
  deadline=$((SECONDS + wait_seconds))
  while true; do
    if curl -fsS --max-time 5 http://127.0.0.1:12345/-/ready >/dev/null 2>&1; then
      alloy_ready=true
      break
    fi
    (( SECONDS >= deadline )) && break
    sleep 2
  done
  if [[ "$alloy_ready" == true ]]; then
    echo "OK   Grafana Alloy ready"
  else
    echo "FAIL Grafana Alloy readiness" >&2
    failed=true
  fi
  if curl -fsS --max-time 10 --output "$metrics_file" \
      http://127.0.0.1:12345/api/v0/component/prometheus.exporter.unix.spark/metrics &&
    grep -q '^node_uname_info' "$metrics_file"; then
    echo "OK   Alloy node exporter host metrics"
  else
    echo "FAIL Alloy node exporter host metrics" >&2
    failed=true
  fi
  if curl -fsS --max-time 10 --output "$metrics_file" http://127.0.0.1:9400/metrics &&
    grep -q '^DCGM_FI_DEV_GPU_UTIL' "$metrics_file"; then
    echo "OK   DCGM GPU metrics"
  else
    echo "FAIL DCGM GPU metrics" >&2
    failed=true
  fi
  alloy_targets_healthy() {
    SPARK_MODE="$SPARK_MODE" EXPECTED_MODEL_TARGETS="$model_target_count" python3 - <<'PY'
import json
import os
import urllib.request

mode = os.environ["SPARK_MODE"]
mode = "models" if mode == "flash" else mode
active = ("node", "dcgm", mode)
inactive = "models" if mode == "comfyui" else "comfyui"
for component in active:
    component = "vllm" if component == "models" else component
    url = f"http://127.0.0.1:12345/api/v0/web/components/prometheus.scrape.{component}"
    with urllib.request.urlopen(url, timeout=5) as response:
        data = json.load(response)
    targets = data.get("debugInfo", [])
    expected = int(os.environ["EXPECTED_MODEL_TARGETS"]) if component == "vllm" else 1
    if len(targets) != expected:
        raise SystemExit(f"Alloy target count mismatch: {component}: expected={expected} actual={len(targets)}")
    for target in targets:
        values = {item["name"]: item["value"].get("value") for item in target.get("body", [])}
        if values.get("health") != "up":
            raise SystemExit(f"Alloy target is down: {component}: {values.get('last_error', '')}")
inactive = "vllm" if inactive == "models" else inactive
url = f"http://127.0.0.1:12345/api/v0/web/components/prometheus.scrape.{inactive}"
with urllib.request.urlopen(url, timeout=5) as response:
    data = json.load(response)
if data.get("debugInfo", []):
    raise SystemExit(f"inactive Alloy target is still configured: {inactive}")
PY
  }
  targets_ready=false
  deadline=$((SECONDS + wait_seconds))
  while true; do
    if alloy_targets_healthy 2>/dev/null; then
      targets_ready=true
      break
    fi
    (( SECONDS >= deadline )) && break
    sleep 2
  done
  if [[ "$targets_ready" == true ]]; then
    echo "OK   Grafana Alloy mode-aware scrape targets"
  else
    alloy_targets_healthy || true
    echo "FAIL Grafana Alloy mode-aware scrape targets" >&2
    failed=true
  fi
  if curl -fsS --max-time 5 --output "$metrics_file" http://127.0.0.1:12345/metrics &&
    python3 - "$metrics_file" <<'PY'
import sys
import time

highest_sent = 0.0
failed = 0.0
for line in open(sys.argv[1]):
    if 'component_id="prometheus.remote_write.metrics_service"' not in line:
        continue
    value = float(line.rsplit(" ", 1)[1])
    if line.startswith("prometheus_remote_storage_queue_highest_sent_timestamp_seconds{"):
        highest_sent = max(highest_sent, value)
    elif line.startswith("prometheus_remote_storage_samples_failed_total{"):
        failed += value
if highest_sent == 0 or time.time() - highest_sent > 60 or failed != 0:
    raise SystemExit(f"remote write unhealthy: lag={time.time() - highest_sent:.1f}s failed={failed:g}")
PY
  then
    echo "OK   Grafana Cloud remote write"
  else
    echo "FAIL Grafana Cloud remote write" >&2
    failed=true
  fi
fi

[[ "$failed" == false ]]
