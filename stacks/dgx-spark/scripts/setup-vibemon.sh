#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
# Version metadata contains no secrets and is reviewed with deployment code.
# Source identity is machine-specific: the environment wins, then the host name.
source_id_override="${VIBEMON_SOURCE_ID:-}"
source_name_override="${VIBEMON_SOURCE_NAME:-}"
# shellcheck disable=SC1091
source "$root/vibemon.env"
VIBEMON_SOURCE_ID="${source_id_override:-$(hostname -s)}"
VIBEMON_SOURCE_NAME="${source_name_override:-DGX Spark}"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/vibemon"
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/vibemon-collector"
data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/vibemon-collector"
unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
unit_path="$unit_dir/dockpad-vibemon-collector.service"
credential_file="$config_dir/collector.env"

[[ "$VIBEMON_COLLECTOR_REVISION" =~ ^[a-f0-9]{40}$ ]] || { echo 'Collector revision must be a full Git SHA.' >&2; exit 2; }
[[ "$VIBEMON_SOURCE_ID" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}$ ]] || { echo 'Invalid source ID.' >&2; exit 2; }
[[ "$VIBEMON_PSUTIL_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Invalid psutil version.' >&2; exit 2; }
for value in "$VIBEMON_SOURCE_NAME" "$VIBEMON_URL" "$config_dir" "$state_dir" "$data_dir" "$unit_dir"; do
  [[ "$value" != *$'\n'* && "$value" != *$'\r'* && "$value" != *'"'* && "$value" != *'%'* && "$value" != *\\* ]] || { echo 'Unsafe value in systemd configuration.' >&2; exit 2; }
done
for command_name in python3 git systemctl loginctl nvidia-smi; do
  command -v "$command_name" >/dev/null || { echo "$command_name is required." >&2; exit 2; }
done
python3 - "$credential_file" "$VIBEMON_URL" <<'PY'
import os, re, stat, sys
from pathlib import Path
from urllib.parse import urlsplit
if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10+ is required.')
p = Path(sys.argv[1])
if not p.is_file() or p.stat().st_uid != os.getuid() or stat.S_IMODE(p.stat().st_mode) & 0o077:
    raise SystemExit('Create an owner-only collector.env containing VIBEMON_WRITE_TOKEN (mode 600).')
if not re.fullmatch(r'VIBEMON_WRITE_TOKEN=vm_[a-f0-9]{60}\n?', p.read_text()):
    raise SystemExit('collector.env must contain only a generated VIBEMON_WRITE_TOKEN assignment.')
url = urlsplit(sys.argv[2])
if any(character.isspace() for character in sys.argv[2]) or url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('', '/'):
    raise SystemExit('VIBEMON_URL must be an HTTPS origin.')
PY
systemctl --user show-environment >/dev/null
if [[ "$(loginctl show-user "$(id -un)" -p Linger --value)" != yes ]]; then
  echo 'Enable user lingering before installing a persistent collector.' >&2
  exit 2
fi
if [[ -f "$unit_path" ]] && ! grep -Fxq '# Managed by dockpad' "$unit_path"; then
  echo "Refusing to overwrite unmanaged $unit_path" >&2
  exit 2
fi
if [[ -e "$data_dir/current" && ! -L "$data_dir/current" ]]; then
  echo 'Refusing to replace an unmanaged collector installation.' >&2
  exit 2
fi
mkdir -p "$unit_dir" "$state_dir" "$data_dir/releases"
chmod 0700 "$state_dir" "$data_dir"
install_dir="$data_dir/releases/$VIBEMON_COLLECTOR_REVISION"
if [[ ! -f "$install_dir/.complete" ]]; then
  python3 -m venv "$install_dir"
  "$install_dir/bin/python" -m pip install --no-cache-dir \
    "psutil==$VIBEMON_PSUTIL_VERSION" \
    "git+https://github.com/opspresso/vibemon-app.git@$VIBEMON_COLLECTOR_REVISION#subdirectory=collector"
  "$install_dir/bin/vibemon-collector" --help >/dev/null
  touch "$install_dir/.complete"
fi
python3 - "$install_dir" "$data_dir/current" <<'PYLINK'
import os, sys, tempfile
from pathlib import Path
current = Path(sys.argv[2])
with tempfile.TemporaryDirectory(dir=current.parent) as directory:
    link = Path(directory) / 'current'
    link.symlink_to(sys.argv[1], target_is_directory=True)
    os.replace(link, current)
PYLINK
temporary="$(mktemp "$unit_dir/.vibemon.XXXXXX")"
trap 'rm -f -- "$temporary"' EXIT
cat > "$temporary" <<UNIT
# Managed by dockpad
[Unit]
Description=VibeMon DGX Spark summary collector
After=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=3

[Service]
EnvironmentFile=$credential_file
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStartPre=/usr/bin/rm -f "$state_dir/health"
ExecStart="$data_dir/current/bin/vibemon-collector" --source-id "$VIBEMON_SOURCE_ID" --name "$VIBEMON_SOURCE_NAME" --url "$VIBEMON_URL" --memory-type unified --disk --health-file "$state_dir/health"
Restart=on-failure
RestartPreventExitStatus=2
RestartSec=15
UMask=0077
NoNewPrivileges=yes
MemoryMax=128M
CPUQuota=25%

[Install]
WantedBy=default.target
UNIT
chmod 0644 "$temporary"
mv "$temporary" "$unit_path"
systemctl --user daemon-reload
systemctl --user enable dockpad-vibemon-collector.service
systemctl --user restart dockpad-vibemon-collector.service
for _ in {1..45}; do
  if "$data_dir/current/bin/python" -m vibemon_collector.health "$state_dir/health"; then
    echo "VibeMon has acknowledged a fresh $VIBEMON_SOURCE_ID summary."
    exit 0
  fi
  if ! systemctl --user is-active --quiet dockpad-vibemon-collector.service; then
    echo 'Collector stopped; inspect journalctl --user -u dockpad-vibemon-collector.service.' >&2
    exit 1
  fi
  sleep 2
done
echo 'Collector has not received a Web acknowledgement within 90 seconds.' >&2
exit 1
