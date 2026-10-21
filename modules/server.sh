# shellcheck shell=bash
# Linux server baseline: timezone, admin packages, fail2ban, TRIM, swap, AWS CLI v2.

DOT_TIMEZONE="${DOT_TIMEZONE:-Asia/Seoul}"
DOT_SWAP_SIZE="${DOT_SWAP_SIZE:-4G}"
SERVER_PACKAGES="ca-certificates curl gnupg unzip git jq htop fail2ban python3 libatomic1"

server::describe() { printf 'Server baseline: timezone, fail2ban, swap, AWS CLI v2\n'; }
server::supported() {
  dot_platform_is ec2 linux && [ "$(uname -s)" = Linux ] && dot_has apt-get && dot_has systemctl
}
server::status() { aws --version 2>/dev/null | cut -d' ' -f1 || printf 'aws not installed\n'; }

_server_timezone() {
  local current
  dot_has timedatectl || return 0
  current=$(timedatectl show -p Timezone --value 2>/dev/null)
  [ "$current" = "$DOT_TIMEZONE" ] && return 0
  dot_sudo timedatectl set-timezone "$DOT_TIMEZONE" && dot_ok "Timezone: $DOT_TIMEZONE"
}

# A new swap file is formatted under a temporary name and published only when
# complete. An existing /swapfile is never reformatted.
_server_swap() {
  if [ -n "$(swapon --show=NAME --noheadings 2>/dev/null)" ]; then
    return 0
  fi
  if [ ! -e /swapfile ]; then
    dot_run "Creating a $DOT_SWAP_SIZE swap file"
    dot_sudo sh -c '
      set -e
      temporary=$(mktemp /swapfile.XXXXXX)
      trap "rm -f \"$temporary\"" EXIT
      fallocate -l "$1" "$temporary"
      chmod 600 "$temporary"
      mkswap "$temporary" >/dev/null
      ln "$temporary" /swapfile
    ' sh "$DOT_SWAP_SIZE" || { dot_warn "Failed to create /swapfile"; return 0; }
  fi
  dot_sudo swapon /swapfile || { dot_warn "Failed to enable /swapfile; inspect it before reformatting"; return 0; }
  grep -qE '^/swapfile[[:space:]]' /etc/fstab ||
    printf '/swapfile none swap sw 0 0\n' | dot_sudo tee -a /etc/fstab >/dev/null
  dot_ok "Swap enabled: /swapfile"
}

# Installs AWS CLI v2 when missing or v1; updates it when due. Each attempt
# uses its own temporary directory, removed on success or failure.
_server_awscli() {
  local version
  version=$(aws --version 2>&1)
  case "$version" in
    aws-cli/2.*) dot_due server || return 0 ;;
  esac
  (
    work=$(mktemp -d) || exit 1
    trap 'rm -rf "$work"' EXIT
    dot_retry "Download AWS CLI" curl -fsSL --connect-timeout 10 \
      -o "$work/awscliv2.zip" "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" || exit 1
    unzip -q "$work/awscliv2.zip" -d "$work" || exit 1
    dot_sudo "$work/aws/install" --update >/dev/null || exit 1
  ) || { dot_warn "AWS CLI v2 installation failed"; return 1; }
  dot_ok "$(aws --version 2>&1 | cut -d' ' -f1)"
}

server::up() {
  local ok=true
  . "$DOT_HOME/modules/apt.sh"
  # shellcheck disable=SC2086
  apt_ensure $SERVER_PACKAGES || dot_die "Failed to install server packages"
  _server_timezone || dot_warn "Failed to set the timezone to $DOT_TIMEZONE"
  dot_sudo systemctl enable --now fail2ban fstrim.timer >/dev/null 2>&1 ||
    dot_warn "Failed to enable fail2ban or fstrim.timer"
  _server_swap
  _server_awscli || ok=false
  dot_due server && [ "$ok" = true ] && dot_stamp server
  dot_ok "Server baseline is current"
}
