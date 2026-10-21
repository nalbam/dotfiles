# shellcheck shell=bash
# Essential APT packages. OS upgrades are a separate, explicit command because
# they can restart services and replace drivers (dot upgrade-system).

APT_PACKAGES="build-essential procps curl file git unzip jq zsh"

apt::describe() { printf 'Essential APT packages (no system upgrade)\n'; }
apt::supported() { [ "$(uname -s)" = Linux ] && dot_has apt-get && dot_has dpkg-query; }

# Prints the packages from $@ that are not fully installed, including packages
# that are unpacked but not configured.
apt_missing() {
  local package status
  for package in "$@"; do
    status=$(dpkg-query -W -f='${Status}' "$package" 2>/dev/null)
    case "$status" in
      'install ok installed' | 'hold ok installed') ;;
      *) printf '%s\n' "$package" ;;
    esac
  done
}

# Installs missing packages; refreshes the index only when something is missing.
apt_ensure() {
  local missing
  # shellcheck disable=SC2086
  missing=$(apt_missing "$@")
  if [ -z "$missing" ]; then
    dot_skip "Installed: $*"
    return 0
  fi
  # shellcheck disable=SC2086
  dot_run "Installing:" $missing
  # shellcheck disable=SC2086
  dot_sudo env DEBIAN_FRONTEND=noninteractive apt-get update -q &&
    dot_sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y -q $missing
}

apt::up() {
  # shellcheck disable=SC2086
  apt_ensure $APT_PACKAGES || dot_die "APT installation failed; resolve the APT error above and run again"
}

# dot upgrade-system: shows pending upgrades; installs them only with --yes.
apt::system_upgrade() {
  local yes="$1"
  apt::supported || { dot_echo "  ✗ No APT on this machine" 1 >&2; return 2; }
  dot_sudo apt-get update -q || return 1
  if [ "$yes" != true ]; then
    apt list --upgradable 2>/dev/null | sed 1d
    dot_info "Nothing changed. Run 'dot upgrade-system --yes' to install these upgrades."
    if dot_platform_is dgx-spark; then
      dot_info "DGX Spark: driver, CUDA, Docker and kernel upgrades restart GPU workloads and need a reboot."
      dot_info "Stop or schedule serving first (dot llm status). NVIDIA also provides updates in DGX Dashboard."
    fi
    return 0
  fi
  if dot_platform_is dgx-spark && dot_has docker &&
     [ -n "$(docker ps -q --filter label=com.docker.compose.project 2>/dev/null)" ]; then
    dot_warn "Compose containers are running; Docker and NVIDIA upgrades restart them"
  fi
  # Keep local configuration files when a package ships a new default, so no prompt blocks the run.
  dot_sudo env DEBIAN_FRONTEND=noninteractive apt-get upgrade -y \
    -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold || return 1
  if [ -f /var/run/reboot-required ]; then
    dot_warn "A reboot is required to finish the upgrade"
  fi
  dot_ok "System packages upgraded"
}
