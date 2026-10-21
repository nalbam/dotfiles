# shellcheck shell=bash
# Docker Engine and Compose from Docker's APT repository (Ubuntu servers).
# DGX OS manages its own Docker and NVIDIA runtime, so DGX Spark is excluded.

DOCKER_PACKAGES="docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"

docker::describe() { printf 'Docker Engine and Compose (Ubuntu servers)\n'; }
docker::supported() {
  dot_platform_is ec2 linux && [ -r /etc/os-release ] && grep -q '^ID=ubuntu' /etc/os-release && dot_has apt-get
}
docker::detect() { dot_has docker; }
docker::status() { docker --version 2>/dev/null || printf 'not installed\n'; }

_docker_repository() {
  local codename architecture
  [ -f /etc/apt/sources.list.d/docker.list ] && return 0
  codename=$(. /etc/os-release && printf '%s' "$VERSION_CODENAME")
  architecture=$(dpkg --print-architecture)
  dot_sudo install -m 0755 -d /etc/apt/keyrings &&
    dot_retry "Download Docker key" dot_sudo curl -fsSL -o /etc/apt/keyrings/docker.asc \
      https://download.docker.com/linux/ubuntu/gpg &&
    dot_sudo chmod a+r /etc/apt/keyrings/docker.asc &&
    printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
      "$architecture" "$codename" | dot_sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
}

# live-restore keeps containers running while dockerd restarts during upgrades.
_docker_live_restore() {
  [ -f /etc/docker/daemon.json ] && grep -q '"live-restore"[[:space:]]*:[[:space:]]*true' /etc/docker/daemon.json
}

docker::up() {
  . "$DOT_HOME/modules/apt.sh"
  if ! dot_has docker; then
    _docker_repository || dot_die "Failed to add Docker's APT repository"
    # shellcheck disable=SC2086
    apt_ensure $DOCKER_PACKAGES || dot_die "Docker installation failed"
    # An existing daemon.json is the machine's choice and is never replaced.
    if [ ! -f /etc/docker/daemon.json ]; then
      printf '%s\n' '{"log-driver":"local","log-opts":{"max-size":"20m","max-file":"5"},"live-restore":true}' |
        dot_sudo tee /etc/docker/daemon.json >/dev/null
    fi
    dot_sudo systemctl enable --now docker >/dev/null && dot_sudo systemctl restart docker ||
      dot_die "Failed to start Docker"
  fi
  if ! id -nG "$(id -un)" | tr ' ' '\n' | grep -qx docker; then
    dot_sudo usermod -aG docker "$(id -un)" && dot_info "Added $(id -un) to the docker group; log in again to use it"
  fi
  if dot_due docker; then
    if _docker_live_restore; then
      # shellcheck disable=SC2086
      dot_sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y -q --only-upgrade $DOCKER_PACKAGES >/dev/null &&
        dot_stamp docker || dot_warn "Docker upgrade failed"
    else
      dot_skip "Docker upgrade skipped: live-restore is off, so an upgrade would stop containers (use dot upgrade-system)"
    fi
  fi
  dot_ok "$(docker --version 2>/dev/null)"
}
