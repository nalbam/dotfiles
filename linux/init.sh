#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
timedatectl set-timezone Asia/Seoul
apt-get update
apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg git jq htop fail2ban
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release; echo $VERSION_CODENAME) stable" >/etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
mkdir -p /opt/compose/{apps,data,backup}
cat >/etc/docker/daemon.json <<EOF
{"log-driver":"local","log-opts":{"max-size":"20m","max-file":"5"},"live-restore":true}
EOF
systemctl enable --now docker fail2ban fstrim.timer
systemctl restart docker
apt-get autoremove -y
apt-get clean
# for ubuntu user
install -m 0600 -D /root/.ssh/authorized_keys /home/ubuntu/.ssh/authorized_keys
chown -R ubuntu:ubuntu /home/ubuntu/.ssh/authorized_keys
