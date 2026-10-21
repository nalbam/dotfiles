# shellcheck shell=bash
# k3s server or agent. Installed with the upstream script; upgraded by replacing
# the binary with the newest release of DOT_K3S_CHANNEL, which keeps the
# service definition, flags and node role unchanged.
#
# First install options (environment or ~/.config/dotfiles/local.env):
#   DOT_K3S_CHANNEL  release channel or minor version, e.g. stable, v1.33 (default: stable)
#   DOT_K3S_URL      server URL; when set, installs an agent
#   DOT_K3S_TOKEN    cluster token for an agent
#   DOT_K3S_EXEC     extra flags, passed as INSTALL_K3S_EXEC

DOT_K3S_CHANNEL="${DOT_K3S_CHANNEL:-stable}"

k3s::describe() { printf 'k3s Kubernetes (server or agent), channel %s\n' "$DOT_K3S_CHANNEL"; }
k3s::supported() { dot_platform_is ec2 linux && [ "$(uname -s)" = Linux ] && dot_has systemctl; }
k3s::detect() { [ -x /usr/local/bin/k3s ]; }
k3s::status() { /usr/local/bin/k3s --version 2>/dev/null | head -1 || printf 'not installed\n'; }

_k3s_service() {
  if systemctl cat k3s-agent.service >/dev/null 2>&1; then printf 'k3s-agent\n'; else printf 'k3s\n'; fi
}

# The channel URL redirects to the release page of the newest version.
_k3s_latest() {
  curl -fsS -o /dev/null -w '%{redirect_url}' "https://update.k3s.io/v1-release/channels/$DOT_K3S_CHANNEL" |
    sed -n 's#.*/releases/tag/##p'
}

_k3s_install() {
  dot_run "Installing k3s ($DOT_K3S_CHANNEL${DOT_K3S_URL:+, agent of $DOT_K3S_URL})"
  INSTALL_K3S_CHANNEL="$DOT_K3S_CHANNEL" INSTALL_K3S_EXEC="${DOT_K3S_EXEC:-}" \
    K3S_URL="${DOT_K3S_URL:-}" K3S_TOKEN="${DOT_K3S_TOKEN:-}" \
    dot_install_script https://get.k3s.io || dot_die "k3s installation failed"
}

# Downloads the release binary, verifies its published SHA-256, then swaps it
# in and restarts the service. Running pods keep running during the restart.
_k3s_upgrade() {
  local version="$1" suffix="" service
  case "$(uname -m)" in
    aarch64 | arm64) suffix="-arm64" ;;
    armv7l) suffix="-armhf" ;;
  esac
  service=$(_k3s_service)
  (
    work=$(mktemp -d) || exit 1
    trap 'rm -rf "$work"' EXIT
    base="https://github.com/k3s-io/k3s/releases/download/$(printf '%s' "$version" | sed 's/+/%2B/g')"
    dot_retry "Download k3s $version" curl -fsSL -o "$work/k3s" "$base/k3s$suffix" &&
      dot_retry "Download checksums" curl -fsSL -o "$work/sums" "$base/sha256sum$(printf '%s' "${suffix:--amd64}").txt" || exit 1
    expected=$(awk -v name="k3s$suffix" '$2 == name { print $1 }' "$work/sums")
    actual=$(sha256sum "$work/k3s" | cut -d' ' -f1)
    [ -n "$expected" ] && [ "$expected" = "$actual" ] || { echo "k3s checksum mismatch" >&2; exit 1; }
    chmod 755 "$work/k3s"
    dot_sudo install -m 755 "$work/k3s" /usr/local/bin/k3s.dot-new &&
      dot_sudo mv -f /usr/local/bin/k3s.dot-new /usr/local/bin/k3s &&
      dot_sudo systemctl restart "$service"
  )
}

k3s::up() {
  local current latest
  if [ ! -x /usr/local/bin/k3s ]; then
    _k3s_install
    dot_stamp k3s
    dot_ok "$(k3s::status)"
    return 0
  fi
  dot_due k3s || { dot_skip "$(k3s::status) checked $(dot_stamp_age k3s)"; return 0; }
  current=$(/usr/local/bin/k3s --version 2>/dev/null | sed -n 's/^k3s version \([^ ]*\).*/\1/p')
  latest=$(_k3s_latest)
  [ -n "$latest" ] || { dot_warn "Could not resolve the newest k3s release for $DOT_K3S_CHANNEL"; return 0; }
  if [ "$current" = "$latest" ]; then
    dot_stamp k3s
    dot_skip "k3s $current is the newest release of $DOT_K3S_CHANNEL"
    return 0
  fi
  dot_run "Upgrading k3s $current -> $latest"
  if _k3s_upgrade "$latest"; then
    dot_stamp k3s
    dot_ok "$(k3s::status)"
  else
    dot_warn "k3s upgrade failed; the installed binary was kept"
  fi
}
