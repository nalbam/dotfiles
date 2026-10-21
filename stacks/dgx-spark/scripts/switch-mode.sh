#!/usr/bin/env bash

set -euo pipefail
# Runs on DGX OS (Bash 5); empty arrays under set -u need Bash 4.4 or newer.
(( BASH_VERSINFO[0] * 100 + BASH_VERSINFO[1] >= 404 )) || { echo "${0##*/} needs Bash 4.4 or newer." >&2; exit 1; }

cd "$(dirname "$0")/.."

target_mode="${1:-}"
[[ "$target_mode" == comfyui || "$target_mode" == models || "$target_mode" == flash ]] || {
  echo "usage: scripts/switch-mode.sh {comfyui|models|flash}" >&2
  exit 1
}
[[ -f .env ]] || { echo ".env is required; deploy Spark first." >&2; exit 1; }

set -a
# shellcheck disable=SC1091
source .env
set +a
current_mode="${SPARK_MODE:-models}"
[[ "$current_mode" == comfyui || "$current_mode" == models || "$current_mode" == flash ]] || {
  echo "invalid current SPARK_MODE: $current_mode" >&2
  exit 1
}

temporary=""
cleanup() {
  [[ -z "$temporary" ]] || rm -f -- "$temporary"
}
trap cleanup EXIT

write_mode() {
  temporary="$(mktemp .env.XXXXXX)"
  awk -v mode="$1" '
    BEGIN { replaced = 0 }
    /^SPARK_MODE=/ { print "SPARK_MODE=" mode; replaced = 1; next }
    { print }
    END { if (!replaced) print "SPARK_MODE=" mode }
  ' .env > "$temporary"
  chmod 0600 "$temporary"
  mv "$temporary" .env
  temporary=""
  export SPARK_MODE="$1"
}

stop_mode() {
  scripts/compose.sh stop-mode "$1"
}

if [[ "$current_mode" == "$target_mode" ]]; then
  scripts/deploy.sh
  HEALTH_WAIT_SECONDS="${HEALTH_WAIT_SECONDS:-1800}" scripts/health-check.sh
  exit 0
fi

write_mode "$target_mode"
if ! PREPARE_ONLY=true scripts/deploy.sh; then
  write_mode "$current_mode"
  echo "failed to prepare $target_mode; keeping $current_mode" >&2
  exit 1
fi

if ! SKIP_PULL=true SKIP_BUILD=true scripts/deploy.sh ||
  ! HEALTH_WAIT_SECONDS="${HEALTH_WAIT_SECONDS:-1800}" scripts/health-check.sh; then
  echo "failed to verify $target_mode; restoring $current_mode" >&2
  stop_mode "$target_mode"
  write_mode "$current_mode"
  SKIP_PULL=true SKIP_BUILD=true scripts/deploy.sh
  HEALTH_WAIT_SECONDS="${HEALTH_WAIT_SECONDS:-1800}" scripts/health-check.sh
  exit 1
fi
echo "== switched Spark mode: $current_mode -> $target_mode"
