# shellcheck shell=bash
# Machine detection. Reads local kernel and firmware files only (no network),
# so it is safe on first boot and inside tests (DOT_SYSROOT prefixes the paths).

DOT_PLATFORMS="macos wsl dgx-spark ec2 rpi linux"

_dot_file_has() {
  [ -r "${DOT_SYSROOT:-}$1" ] && grep -qi -- "$2" "${DOT_SYSROOT:-}$1" 2>/dev/null
}

_dot_file_starts() {
  local value
  value=$(head -c 64 "${DOT_SYSROOT:-}$1" 2>/dev/null) || return 1
  case "$value" in
    "$2"*) return 0 ;;
  esac
  return 1
}

# Prints the detected platform: macos, wsl, dgx-spark, ec2, rpi or linux.
dot_detect_platform() {
  case "$(uname -s)" in
    Darwin) printf 'macos\n'; return ;;
    Linux) ;;
    *) printf 'unsupported\n'; return ;;
  esac
  if [ -n "${WSL_DISTRO_NAME:-}" ] || _dot_file_has /proc/sys/kernel/osrelease microsoft; then
    printf 'wsl\n'
  elif _dot_file_has /etc/dgx-release 'DGX Spark' ||
       _dot_file_has /sys/devices/virtual/dmi/id/product_name 'DGX_Spark'; then
    printf 'dgx-spark\n'
  elif _dot_file_has /sys/devices/virtual/dmi/id/sys_vendor 'Amazon EC2' ||
       _dot_file_starts /sys/devices/virtual/dmi/id/board_asset_tag 'i-' ||
       _dot_file_starts /sys/hypervisor/uuid 'ec2'; then
    printf 'ec2\n'
  elif _dot_file_has /proc/device-tree/model 'Raspberry Pi'; then
    printf 'rpi\n'
  else
    printf 'linux\n'
  fi
}

# Sets DOT_OS, DOT_ARCH and DOT_PLATFORM. An explicit DOT_PLATFORM or the
# override saved by `dot platform set` takes precedence over detection.
dot_detect() {
  DOT_OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
  DOT_ARCH="$(uname -m)"
  DOT_PLATFORM_SOURCE=detected
  if [ -n "${DOT_PLATFORM:-}" ]; then
    DOT_PLATFORM_SOURCE=environment
  elif [ -s "$DOT_CONFIG/platform" ]; then
    DOT_PLATFORM="$(tr -d '[:space:]' < "$DOT_CONFIG/platform")"
    DOT_PLATFORM_SOURCE=override
  else
    DOT_PLATFORM="$(dot_detect_platform)"
  fi
  case " $DOT_PLATFORMS " in
    *" $DOT_PLATFORM "*) ;;
    *) return 1 ;;
  esac
  export DOT_OS DOT_ARCH DOT_PLATFORM
}

dot_platform_is() {
  local platform
  for platform in "$@"; do
    [ "$DOT_PLATFORM" = "$platform" ] && return 0
  done
  return 1
}
