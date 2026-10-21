#!/usr/bin/env bash

set -euo pipefail

root="$(cd "$(dirname "$0")" && pwd)"
usage() {
  echo "Usage: $0 [--dry-run] DASHBOARD_NAME_OR_JSON_FILE"
}

dry_run=false
dashboard=""
for argument in "$@"; do
  case "$argument" in
    --dry-run) dry_run=true ;;
    --help|-h) usage; exit 0 ;;
    -*) usage >&2; exit 1 ;;
    *)
      [[ -z "$dashboard" ]] || { usage >&2; exit 1; }
      dashboard="$argument"
      ;;
  esac
done
[[ -n "$dashboard" ]] || { usage >&2; exit 1; }
if [[ -f "$dashboard" ]]; then
  dashboard_file="$dashboard"
elif [[ "$dashboard" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  dashboard_file="$root/dashboards/$dashboard.json"
else
  echo "Dashboard file not found: $dashboard" >&2
  exit 1
fi

command -v jq >/dev/null || { echo "jq is required." >&2; exit 1; }
jq -se 'length == 1 and (.[0] | type == "object" and
  (.uid | type == "string" and test("^[a-zA-Z0-9_-]{1,40}$")) and
  (.title | type == "string" and length > 0) and (.panels | type == "array"))' \
  "$dashboard_file" >/dev/null
dashboard_uid="$(jq -r .uid "$dashboard_file")"
folder_uid="${GRAFANA_FOLDER_UID:-}"

create_payload() {
  jq -n --slurpfile dashboard "$dashboard_file" --arg folder "$folder_uid" \
    --arg datasource "${GRAFANA_DATASOURCE_UID:-}" '
    {dashboard: ($dashboard[0] | .id = null | .version = 0 |
      if $datasource != "" then
        .templating.list |= map(if .name == "datasource" and .type == "datasource"
          then .current = {text: $datasource, value: $datasource, selected: true} else . end)
      else . end),
     folderUid: $folder, overwrite: true, message: "Update from dotfiles/stacks/grafana"}'
}

if [[ "$dry_run" == true ]]; then
  create_payload
  exit 0
fi

command -v curl >/dev/null || { echo "curl is required." >&2; exit 1; }
: "${GRAFANA_URL:?Set the target Grafana URL}"
GRAFANA_URL=${GRAFANA_URL%/}
[[ "$GRAFANA_URL" == https://* || "$GRAFANA_URL" == http://* ]] || {
  echo "GRAFANA_URL must use http:// or https://" >&2; exit 1;
}
if [[ -z "${GRAFANA_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
  if [[ -t 0 ]]; then
    read -rsp "Grafana service account token: " GRAFANA_SERVICE_ACCOUNT_TOKEN
    echo
  else
    echo "GRAFANA_SERVICE_ACCOUNT_TOKEN is required in non-interactive mode." >&2
    exit 1
  fi
fi
: "${GRAFANA_SERVICE_ACCOUNT_TOKEN:?Grafana service account token is empty}"

umask 077
temp_dir="$(mktemp -d)"
trap 'rm -rf -- "$temp_dir"' EXIT
printf 'Authorization: Bearer %s\n' "$GRAFANA_SERVICE_ACCOUNT_TOKEN" > "$temp_dir/auth-header"
curl_args=(-sS --connect-timeout 10 --max-time 60 --retry 3 --retry-delay 2
  --header "@$temp_dir/auth-header")
status="$(curl "${curl_args[@]}" -o "$temp_dir/current.json" -w '%{http_code}' \
  -H 'Accept: application/json' "$GRAFANA_URL/api/dashboards/uid/$dashboard_uid")"
case "$status" in
  200)
    action=updated
    if [[ -z "${GRAFANA_FOLDER_UID+x}" ]]; then
      folder_uid="$(jq -r '.meta.folderUid // ""' "$temp_dir/current.json")"
    fi
    ;;
  404) action=created ;;
  *) echo "Grafana dashboard lookup failed with HTTP $status" >&2; exit 1 ;;
esac

create_payload > "$temp_dir/payload.json"
status="$(curl "${curl_args[@]}" -o "$temp_dir/response.json" -w '%{http_code}' \
  -X POST -H 'Content-Type: application/json' \
  --data-binary "@$temp_dir/payload.json" "$GRAFANA_URL/api/dashboards/db")"
if [[ "$status" != 2* ]]; then
  echo "Grafana dashboard write failed with HTTP $status" >&2
  exit 1
fi

dashboard_path="$(jq -r '.url // empty' "$temp_dir/response.json")"
echo "Dashboard $action: $GRAFANA_URL${dashboard_path:-/d/$dashboard_uid}"
