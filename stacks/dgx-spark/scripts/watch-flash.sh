#!/usr/bin/env bash
set -euo pipefail
# Runs on DGX OS (Bash 5); empty arrays under set -u need Bash 4.4 or newer.
(( BASH_VERSINFO[0] * 100 + BASH_VERSINFO[1] >= 404 )) || { echo "${0##*/} needs Bash 4.4 or newer." >&2; exit 1; }

# Keep host memory above the serving reserve floors; a manual Docker stop prevents restart.
container=dgx-spark-flash-1
below_available=0
below_free=0
while true; do
  running="$(docker ps --filter name="^/$container$" \
    --filter label=io.dockpad.flash-recipe=tensorfold --format '{{.ID}}')"
  if [[ -z "$running" ]]; then
    below_available=0
    below_free=0
    sleep 10
    continue
  fi
  read -r available free < <(awk '
    /^MemAvailable:/ { available = $2 }
    /^MemFree:/ { free = $2 }
    END { print available, free }
  ' /proc/meminfo)
  if (( available < 6 * 1048576 )); then
    below_available=$((below_available + 1))
  else
    below_available=0
  fi
  if (( free < 2 * 1048576 && available < 10 * 1048576 )); then
    below_free=$((below_free + 1))
  else
    below_free=0
  fi
  if (( below_available >= 5 || below_free >= 5 )); then
    echo "Stopping Flash: MemAvailable=$((available / 1048576)) GiB, MemFree=$((free / 1048576)) GiB"
    docker stop --time 30 "$container"
    below_available=0
    below_free=0
  fi
  sleep 1
done
