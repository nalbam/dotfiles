#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

# Account-specific values live only in the runtime .env.grafana, never in this repository.
GRAFANA_KEYS=(GCLOUD_FM_URL GCLOUD_FM_USERNAME GCLOUD_PROM_URL GCLOUD_PROM_USERNAME GCLOUD_FM_COLLECTOR_ID GCLOUD_RW_API_KEY)

existing_environment_value() {
  local key="$1"
  (
    unset "${GRAFANA_KEYS[@]}"
    # shellcheck disable=SC1091
    source .env.grafana
    printf '%s' "${!key-}"
  )
}

if [[ -s .env.grafana ]]; then
  for key in "${GRAFANA_KEYS[@]}"; do
    if [[ -z "${!key:-}" ]]; then
      printf -v "$key" '%s' "$(existing_environment_value "$key")"
    fi
  done
fi

# Prompt for a missing value on a terminal; a non-interactive run must provide it.
require_value() {
  local key="$1" label="$2" secret="${3:-false}"
  [[ -z "${!key:-}" ]] || return 0
  if [[ ! -t 0 ]]; then
    echo "$key is required in non-interactive mode." >&2
    exit 1
  fi
  if [[ "$secret" == true ]]; then
    read -rsp "$label: " "$key"
    echo
  else
    read -rp "$label: " "$key"
  fi
  [[ -n "${!key:-}" ]] || { echo "$label is empty." >&2; exit 1; }
}

require_value GCLOUD_FM_URL "Grafana Cloud Fleet Management URL (https://fleet-management-...grafana.net)"
require_value GCLOUD_FM_USERNAME "Grafana Cloud Fleet Management user ID (digits)"
require_value GCLOUD_PROM_URL "Grafana Cloud Prometheus remote-write URL (https://.../api/prom/push)"
require_value GCLOUD_PROM_USERNAME "Grafana Cloud Prometheus user ID (digits)"
require_value GCLOUD_RW_API_KEY "Grafana Cloud access policy token" true
: "${GCLOUD_FM_COLLECTOR_ID:=$(hostname -s)}"

for key in "${GRAFANA_KEYS[@]}"; do
  if [[ "${!key}" == *$'\n'* ]]; then
    echo "Grafana environment values must not contain newlines." >&2
    exit 1
  fi
done
for key in GCLOUD_FM_USERNAME GCLOUD_PROM_USERNAME; do
  [[ "${!key}" =~ ^[0-9]+$ ]] || { echo "$key must contain only digits." >&2; exit 1; }
done
for key in GCLOUD_FM_URL GCLOUD_PROM_URL; do
  [[ "${!key}" =~ ^https://[A-Za-z0-9.-]+(/[A-Za-z0-9._/-]*)?$ ]] || { echo "$key must be an HTTPS URL." >&2; exit 1; }
done

temporary="$(mktemp .env.grafana.XXXXXX)"
metrics_file="$(mktemp)"
cleanup() {
  rm -f -- "$temporary"
  rm -f -- "$metrics_file"
}
trap cleanup EXIT
chmod 0600 "$temporary"
escape_environment_value() {
  local value=${1//\\/\\\\}
  value=${value//\"/\\\"}
  printf '"%s"' "$value"
}
for key in "${GRAFANA_KEYS[@]}"; do
  printf '%s=' "$key"
  escape_environment_value "${!key}"
  printf '\n'
done > "$temporary"
mv "$temporary" .env.grafana
temporary=""

(
  # shellcheck disable=SC1091
  [[ ! -f .env ]] || source .env
  python3 -B scripts/services.py write-targets "${SPARK_MODE:-models}"
)
docker compose --profile monitoring config --quiet
docker compose --profile monitoring pull dcgm-exporter alloy
docker compose --profile monitoring run --rm --no-deps alloy validate /etc/alloy/config.alloy
docker compose --profile monitoring up -d dcgm-exporter alloy

for _ in {1..30}; do
  if curl -fsS http://127.0.0.1:12345/-/ready >/dev/null &&
    curl -fsS --output "$metrics_file" http://127.0.0.1:9400/metrics &&
    grep -q '^DCGM_FI_DEV_GPU_UTIL' "$metrics_file"; then
    echo "Grafana Alloy and DCGM Exporter are ready."
    echo "Collector ID: $GCLOUD_FM_COLLECTOR_ID"
    exit 0
  fi
  sleep 2
done

docker compose --profile monitoring logs --tail 100 alloy dcgm-exporter >&2
exit 1
