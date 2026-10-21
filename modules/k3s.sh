# shellcheck shell=bash
# k3s server or agent. Installed with the upstream script; upgraded by replacing
# the binary, which keeps the service definition, flags and node role.
#
# Settings (environment or ~/.config/dotfiles/local.env):
#   DOT_K3S_CHANNEL  release channel: a minor version such as v1.33, or stable.
#                    Default: stable for a new install, the installed minor
#                    version for an existing one (patch upgrades only).
#   DOT_K3S_URL      server URL; when set, the first install creates an agent
#   DOT_K3S_TOKEN    cluster token for an agent (keep it in local.env, mode 600)
#   DOT_K3S_EXEC     extra flags for the first install, passed as INSTALL_K3S_EXEC
#
# Kubernetes supports one minor version per upgrade, servers before agents, so
# an upgrade that would skip a minor version is refused.

# The installed binary; DOT_SYSROOT lets tests and detection use a fixture root.
K3S_BIN="${DOT_SYSROOT:-}/usr/local/bin/k3s"

k3s::describe() { printf 'k3s Kubernetes (server or agent)\n'; }
k3s::supported() { dot_platform_is ec2 linux && [ "$(uname -s)" = Linux ] && dot_has systemctl; }
k3s::detect() { [ -x "$K3S_BIN" ]; }
k3s::status() {
  if [ -x "$K3S_BIN" ]; then
    printf '%s (%s)\n' "$(_k3s_version)" "$(_k3s_channel)"
  else
    printf 'not installed\n'
  fi
}

_k3s_version() {
  "$K3S_BIN" --version 2>/dev/null | sed -n 's/^k3s version \([^ ]*\).*/\1/p' | head -1
}

# vX.Y of a version such as v1.33.4+k3s1.
_k3s_minor() { printf '%s\n' "$1" | sed -n 's/^\(v[0-9]*\.[0-9]*\)\..*/\1/p'; }

_k3s_channel() {
  if [ -n "${DOT_K3S_CHANNEL:-}" ]; then
    printf '%s\n' "$DOT_K3S_CHANNEL"
  elif [ -x "$K3S_BIN" ]; then
    _k3s_minor "$(_k3s_version)"
  else
    printf 'stable\n'
  fi
}

_k3s_service() {
  if systemctl cat k3s-agent.service >/dev/null 2>&1; then printf 'k3s-agent\n'; else printf 'k3s\n'; fi
}

# The channel URL redirects to the release page of the newest version.
_k3s_latest() {
  curl -fsS -o /dev/null -w '%{redirect_url}' "https://update.k3s.io/v1-release/channels/$1" |
    sed -n 's#.*/releases/tag/##p'
}

_k3s_install() {
  local channel
  channel=$(_k3s_channel)
  dot_run "Installing k3s ($channel${DOT_K3S_URL:+, agent of $DOT_K3S_URL})"
  INSTALL_K3S_CHANNEL="$channel" INSTALL_K3S_EXEC="${DOT_K3S_EXEC:-}" \
    K3S_URL="${DOT_K3S_URL:-}" K3S_TOKEN="${DOT_K3S_TOKEN:-}" \
    dot_install_script https://get.k3s.io || dot_die "k3s installation failed"
}

# Downloads the release binary, verifies its published SHA-256, then swaps it
# in and restarts the service. Running pods keep running during the restart.
_k3s_upgrade() {
  local version="$1" binary sums service
  case "$(uname -m)" in
    aarch64 | arm64) binary=k3s-arm64; sums=sha256sum-arm64.txt ;;
    armv7l) binary=k3s-armhf; sums=sha256sum-arm.txt ;;
    *) binary=k3s; sums=sha256sum-amd64.txt ;;
  esac
  service=$(_k3s_service)
  (
    work=$(mktemp -d) || exit 1
    trap 'rm -rf "$work"' EXIT
    base="https://github.com/k3s-io/k3s/releases/download/$(printf '%s' "$version" | sed 's/+/%2B/g')"
    dot_retry "Download k3s $version" curl -fsSL -o "$work/k3s" "$base/$binary" &&
      dot_retry "Download checksums" curl -fsSL -o "$work/sums" "$base/$sums" || exit 1
    expected=$(awk -v name="$binary" '$2 == name { print $1 }' "$work/sums")
    actual=$(sha256sum "$work/k3s" | cut -d' ' -f1)
    [ -n "$expected" ] && [ "$expected" = "$actual" ] || { echo "k3s checksum mismatch" >&2; exit 1; }
    chmod 755 "$work/k3s"
    dot_sudo install -m 755 "$work/k3s" /usr/local/bin/k3s.dot-new &&
      dot_sudo mv -f /usr/local/bin/k3s.dot-new /usr/local/bin/k3s &&
      dot_sudo systemctl restart "$service"
  )
}

k3s::up() {
  local current latest channel current_minor latest_minor
  if [ ! -x "$K3S_BIN" ]; then
    _k3s_install
    dot_stamp k3s
    dot_ok "k3s $(k3s::status)"
    return 0
  fi
  dot_due k3s || { dot_skip "k3s $(_k3s_version) checked $(dot_stamp_age k3s)"; return 0; }
  current=$(_k3s_version)
  channel=$(_k3s_channel)
  latest=$(_k3s_latest "$channel")
  [ -n "$current" ] || { dot_warn "Could not read the installed k3s version"; return 0; }
  [ -n "$latest" ] || { dot_warn "Could not resolve the newest k3s release for $channel"; return 0; }
  if [ "$current" = "$latest" ]; then
    dot_stamp k3s
    dot_skip "k3s $current is the newest release of $channel"
    return 0
  fi
  # Minor numbers of v1.X versions.
  current_minor=$(_k3s_minor "$current"); current_minor=${current_minor#v1.}
  latest_minor=$(_k3s_minor "$latest"); latest_minor=${latest_minor#v1.}
  case "$current_minor" in
    '' | *[!0-9]*) dot_warn "Unexpected k3s version: $current"; return 0 ;;
  esac
  case "$latest_minor" in
    '' | *[!0-9]*) dot_warn "Unexpected k3s release for $channel: $latest"; return 0 ;;
  esac
  if [ "$latest_minor" -lt "$current_minor" ]; then
    dot_warn "k3s $current is newer than channel $channel ($latest); nothing to do"
    return 0
  fi
  if [ "$latest_minor" -gt $((current_minor + 1)) ]; then
    dot_warn "k3s $current -> $latest skips a minor version; set DOT_K3S_CHANNEL=v1.$((current_minor + 1)) and upgrade servers before agents"
    return 0
  fi
  dot_run "Upgrading k3s $current -> $latest ($(_k3s_service))"
  if _k3s_upgrade "$latest"; then
    dot_stamp k3s
    dot_ok "k3s $(_k3s_version)"
  else
    dot_warn "k3s upgrade failed; the installed binary was kept"
  fi
}
