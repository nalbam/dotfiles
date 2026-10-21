# shellcheck shell=bash
# Docker Engine and Compose from Docker's APT repository (Ubuntu servers).
# DGX OS manages its own Docker and NVIDIA runtime, so DGX Spark is excluded.
# Upgrades restart dockerd and containerd, so they run only through
# `dot upgrade-system`; this module installs and checks.

DOCKER_PACKAGES="docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"

docker::describe() { printf 'Docker Engine and Compose (Ubuntu servers)\n'; }
docker::supported() {
  dot_platform_is ec2 linux && grep -qs '^ID=ubuntu' "${DOT_SYSROOT:-}/etc/os-release" && dot_has apt-get
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

docker::up() {
  . "$DOT_HOME/modules/apt.sh"
  if dot_has docker; then
    dot_ok "$(docker --version 2>/dev/null); upgrades run with dot upgrade-system"
    return 0
  fi
  _docker_repository || dot_die "Failed to add Docker's APT repository"
  # shellcheck disable=SC2086
  apt_ensure $DOCKER_PACKAGES || dot_die "Docker installation failed"
  # An existing daemon.json is the machine's choice and is never replaced.
  # live-restore keeps containers running while dockerd restarts.
  if [ ! -f "${DOT_SYSROOT:-}/etc/docker/daemon.json" ]; then
    printf '%s\n' '{"log-driver":"local","log-opts":{"max-size":"20m","max-file":"5"},"live-restore":true}' |
      dot_sudo tee /etc/docker/daemon.json >/dev/null
  fi
  dot_sudo systemctl enable --now docker >/dev/null && dot_sudo systemctl restart docker ||
    dot_die "Failed to start Docker"
  # Membership grants root-equivalent access, so it is granted only on install.
  dot_sudo usermod -aG docker "$(id -un)" && dot_info "Added $(id -un) to the docker group; log in again to use it"
  dot_ok "$(docker --version 2>/dev/null)"
}
