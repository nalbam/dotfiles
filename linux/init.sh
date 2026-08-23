#!/bin/bash
#
# curl -fsSL nalbam.github.io/dotfiles/linux/init.sh | bash
#
# Run as root on a fresh Ubuntu host. Idempotent — rerun after a broken run.
# Everything after this belongs to the ubuntu user.

set -e

((EUID == 0)) || { echo "Run this as root." >&2; exit 1; }

[[ -r /etc/os-release ]] || { echo "Cannot identify this operating system." >&2; exit 1; }
# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == "ubuntu" ]] || { echo "Ubuntu only; found ${PRETTY_NAME:-unknown}." >&2; exit 1; }
[[ "${VERSION_ID:-}" == "24.04" ]] || echo "Warning: tested on Ubuntu 24.04, found ${PRETTY_NAME:-unknown}." >&2

export DEBIAN_FRONTEND=noninteractive
timedatectl set-timezone Asia/Seoul
apt-get update
apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg unzip git jq htop fail2ban python3 gh libatomic1

# docker
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" >/etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
cat >/etc/docker/daemon.json <<EOF
{"log-driver":"local","log-opts":{"max-size":"20m","max-file":"5"},"live-restore":true}
EOF
systemctl enable --now docker fail2ban fstrim.timer
systemctl restart docker

# aws cli
if command -v aws >/dev/null && aws --version 2>&1 | grep -q '^aws-cli/2\.'; then
  echo "$(aws --version 2>&1) is already installed"
else
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o /tmp/awscliv2.zip
  unzip -q /tmp/awscliv2.zip -d /tmp
  /tmp/aws/install --update
  rm -rf /tmp/awscliv2.zip /tmp/aws
fi

# swap
if [[ ! -e /swapfile ]]; then
  fallocate -l 4G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile >/dev/null
fi
swapon --show=NAME --noheadings | tr -d ' ' | grep -qx /swapfile || swapon /swapfile
grep -qE '^/swapfile[[:space:]]' /etc/fstab || echo '/swapfile none swap sw 0 0' >>/etc/fstab

mkdir -p /opt/compose/{apps,data,backup}

apt-get autoremove -y
apt-get clean

# for ubuntu user
if id -u ubuntu >/dev/null 2>&1; then
  if [[ -f /root/.ssh/authorized_keys ]]; then
    install -d -m 0700 -o ubuntu -g ubuntu /home/ubuntu/.ssh
    install -m 0600 -o ubuntu -g ubuntu /root/.ssh/authorized_keys /home/ubuntu/.ssh/authorized_keys
  fi
  usermod -aG docker ubuntu
  chown -R ubuntu:ubuntu /opt/compose
fi

echo
docker --version
docker compose version
aws --version
swapon --show
echo "Host is ready. Continue as the ubuntu user."
