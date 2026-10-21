#!/usr/bin/env bash
set -euo pipefail
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/vibemon"
[[ -s "$config_dir/collector.env" ]] || exit 0
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/vibemon-collector"
data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/vibemon-collector"
systemctl --user is-active --quiet dockpad-vibemon-collector.service
"$data_dir/current/bin/python" -m vibemon_collector.health "$state_dir/health"
echo 'OK   VibeMon fresh delivery'
