#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

SPARK_MODE="${SPARK_MODE:-models}"
[[ "$SPARK_MODE" == comfyui || "$SPARK_MODE" == models || "$SPARK_MODE" == flash ]] || { echo "SPARK_MODE must be comfyui, models or flash." >&2; exit 1; }

compose=(docker compose --profile "$SPARK_MODE")
if [[ -s .env.grafana ]]; then
  compose+=(--profile monitoring)
fi

action="${1:-}"
(( $# == 0 )) || shift

case "$action" in
  up) "${compose[@]}" up "$@" ;;
  ps) "${compose[@]}" ps "$@" ;;
  ps-json) "${compose[@]}" ps --all --format json "$@" ;;
  config) "${compose[@]}" config "$@" ;;
  config-json) "${compose[@]}" config --format json "$@" ;;
  has-service)
    service="${1:?service is required}"
    "${compose[@]}" config --services | grep -Fxq "$service"
    ;;
  stop-mode)
    mode="${1:?mode is required}"
    members="$(python3 -B scripts/services.py list "$mode")"
    services=()
    while IFS= read -r service; do
      [[ -z "$service" ]] || services+=("$service")
    done <<< "$members"
    if (( ${#services[@]} > 0 )); then
      docker compose --profile "$mode" stop "${services[@]}"
    fi
    ;;
  service)
    operation="${1:?operation is required}"
    service="${2:?service is required}"
    shift 2
    "${compose[@]}" "$operation" "$service" "$@"
    ;;
  logs) "${compose[@]}" logs "$@" ;;
  *) echo "usage: scripts/compose.sh {up|ps|ps-json|config|config-json|has-service|stop-mode|service|logs}" >&2; exit 1 ;;
esac
