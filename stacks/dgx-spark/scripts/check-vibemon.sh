#!/usr/bin/env bash
set -euo pipefail
# Runs on DGX OS (Bash 5); empty arrays under set -u need Bash 4.4 or newer.
(( BASH_VERSINFO[0] * 100 + BASH_VERSINFO[1] >= 404 )) || { echo "${0##*/} needs Bash 4.4 or newer." >&2; exit 1; }
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/vibemon"
[[ -s "$config_dir/collector.env" ]] || exit 0
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/vibemon-collector"
data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/vibemon-collector"
systemctl --user is-active --quiet dockpad-vibemon-collector.service
"$data_dir/current/bin/python" -m vibemon_collector.health "$state_dir/health"
echo 'OK   VibeMon fresh delivery'
