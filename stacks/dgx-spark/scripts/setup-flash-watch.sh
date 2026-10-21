#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
unit_directory="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
unit_path="$unit_directory/dockpad-flash-memory-watch.service"
if [[ -f "$unit_path" ]] && ! grep -Fxq '# Managed by dockpad' "$unit_path"; then
  echo "Refusing to overwrite unmanaged $unit_path" >&2
  exit 1
fi
mkdir -p "$unit_directory"
temporary="$(mktemp "$unit_directory/.flash-watch.XXXXXX")"
trap 'rm -f -- "$temporary"' EXIT
cat > "$temporary" <<EOF
# Managed by dockpad
[Unit]
Description=DGX Spark Flash memory watchdog

[Service]
ExecStart=/usr/bin/bash "$root/scripts/watch-flash.sh"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF
chmod 0644 "$temporary"
mv "$temporary" "$unit_path"
systemctl --user daemon-reload
systemctl --user enable dockpad-flash-memory-watch.service
# A running shell keeps the old loop body after deployment changes its script.
systemctl --user restart dockpad-flash-memory-watch.service
