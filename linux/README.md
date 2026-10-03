# Ubuntu server setup

Use `init.sh` to prepare a fresh Ubuntu server for Docker workloads. The script identifies Ubuntu and notes Ubuntu 24.04 as its tested version. It is separate from the user-level [dotfiles installer](../README.md#quick-start).

## Before running

- Run as root, or use a user with sudo access. Network access and space for packages and a 4 GiB swap file are required.
- Review an existing host before applying this setup. The script upgrades packages, sets the timezone to `Asia/Seoul`, replaces `/etc/docker/daemon.json`, and restarts Docker.
- If the `ubuntu` user exists, the script grants Docker group membership and ownership of `/opt/compose`. If root has `authorized_keys`, it copies that file over the user's `authorized_keys`.

## Run

From the repository root:

```bash
sudo bash linux/init.sh
```

For a host without a checkout, run this from a root shell:

```bash
curl -fsSL https://nalbam.github.io/dotfiles/linux/init.sh | bash
```

The script installs system packages, Docker Engine and Compose, AWS CLI v2, fail2ban, and swap. It prepares `/opt/compose/apps`, `/opt/compose/data`, and `/opt/compose/backup`.

## Verify and continue

The final output includes Docker, Compose, and AWS CLI versions and the active swap devices. Verify Docker and swap with:

```bash
sudo docker info
swapon --show
```

The script stops when a command fails. Read the failing command, resolve its cause, and review any existing Docker configuration before rerunning. Package upgrades and replaced files are not rolled back.

If the `ubuntu` user exists, log in with a new session before using its Docker group membership. Install the user-level dotfiles separately under that user.
