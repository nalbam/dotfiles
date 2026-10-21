# shellcheck shell=bash
# Shared helpers for bin/dot and modules. Must stay compatible with Bash 3.2
# (macOS /bin/bash): no associative arrays, no ${var,,}, no mapfile.

DOT_HOME="${DOT_HOME:-$HOME/.dotfiles}"
DOT_CONFIG="${DOT_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/dotfiles}"
DOT_STATE="${DOT_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles}"
DOT_REPO_URL="${DOT_REPO_URL:-https://github.com/nalbam/dotfiles.git}"
DOT_UPGRADE_INTERVAL="${DOT_UPGRADE_INTERVAL:-21600}"
DOT_FORCE="${DOT_FORCE:-false}"

################################################################################
# Output
################################################################################

if [ -z "${DOT_COLOR+x}" ]; then
  if [ -t 1 ] && command -v tput >/dev/null 2>&1 && [ "${TERM:-dumb}" != dumb ]; then
    DOT_COLOR=true
  else
    DOT_COLOR=false
  fi
fi

dot_echo() {
  if [ "$DOT_COLOR" = true ] && [ -n "${2:-}" ]; then
    printf '%s%b%s\n' "$(tput setaf "$2")" "$1" "$(tput sgr0)"
  else
    printf '%b\n' "$1"
  fi
}

dot_title() { dot_echo "\n▶ $*" 6; }
dot_info() { dot_echo "  ℹ $*" 4; }
dot_ok() { dot_echo "  ✓ $*" 2; }
dot_skip() { dot_echo "  ⊘ $*" 3; }
dot_run() { dot_echo "  → $*" 5; }

# Modules run in subshells, so warnings are counted in a file shared by the run.
dot_warn() {
  if [ -n "${DOT_WARN_FILE:-}" ]; then
    printf '%s\n' "$*" >> "$DOT_WARN_FILE"
  fi
  dot_echo "  ⚠ $*" 3
}

dot_die() {
  dot_echo "  ✗ $*" 1 >&2
  exit 1
}

################################################################################
# Commands and downloads
################################################################################

dot_has() { command -v "$1" >/dev/null 2>&1; }

dot_sudo() {
  if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi
}

# At most three attempts, waiting 5s then 10s. Command diagnostics stay visible.
dot_retry() {
  local description="$1" attempt=1 wait_time=5
  shift
  while :; do
    if "$@"; then return 0; fi
    [ "$attempt" -lt 3 ] || return 1
    dot_info "$description failed, retrying in ${wait_time}s (attempt $attempt/3)"
    sleep "$wait_time"
    attempt=$((attempt + 1))
    wait_time=$((wait_time * 2))
  done
}

# Run a downloaded installer only when the transfer completed and the script parses.
dot_install_script() (
  local url="$1" script
  shift
  script=$(mktemp "${TMPDIR:-/tmp}/dot-bootstrap.XXXXXX") || return
  trap 'rm -f "$script"' EXIT
  dot_retry "Download $url" curl -fsSL --connect-timeout 10 -o "$script" "$url" || return
  /bin/bash -n "$script" || return
  /bin/bash "$script" "$@"
)

################################################################################
# Files
################################################################################

dot_md5() {
  if dot_has md5sum; then
    local digest
    digest=$(md5sum "$1") || return
    printf '%s\n' "${digest%% *}"
  else
    md5 -q "$1"
  fi
}

# 0: equal, 1: different, 2: comparison failed. Never treats a failed checksum as equal.
dot_same_file() {
  local left right
  [ -f "$1" ] && [ -f "$2" ] || return 1
  left=$(dot_md5 "$1") || return 2
  right=$(dot_md5 "$2") || return 2
  [ -n "$left" ] && [ -n "$right" ] || return 2
  [ "$left" = "$right" ]
}

# Keep the previous content at <file>.backup (mode 600) without following links.
dot_backup() {
  local temporary
  [ -f "$1" ] || return 0
  if [ -L "$1.backup" ] || { [ -e "$1.backup" ] && [ ! -f "$1.backup" ]; }; then
    return 1
  fi
  temporary=$(mktemp "$1.backup.tmp.XXXXXX") || return 1
  if ! { cp "$1" "$temporary" && chmod 600 "$temporary" && mv -f "$temporary" "$1.backup"; }; then
    rm -f "$temporary"
    return 1
  fi
  dot_info "Backup: $1.backup"
}

# Prints the permission bits of FILE, or the umask default for a new file.
dot_file_mode() {
  if [ -f "$1" ]; then
    stat -c %a "$1" 2>/dev/null || stat -f %Lp "$1"
  else
    printf '%o\n' $((0666 & ~$(umask)))
  fi
}

# dot_install_file TARGET SOURCE [MODE]
# TARGET is relative to $HOME, SOURCE to $DOT_HOME. Identical content is left
# untouched; changed content is backed up, staged and replaced atomically.
dot_install_file() {
  local target="$HOME/$1" source="$DOT_HOME/$2" mode="${3:-}" temporary comparison
  [ -f "$source" ] || dot_die "Missing source: $2"
  if [ -e "$target" ] && [ ! -f "$target" ]; then
    dot_die "Expected a file at $target"
  fi
  mkdir -p "${target%/*}" || dot_die "Failed to create ${target%/*}"

  dot_same_file "$source" "$target"
  comparison=$?
  if [ "$comparison" -eq 2 ]; then
    dot_die "Failed to compare $2 with $target"
  elif [ "$comparison" -eq 1 ]; then
    temporary=$(mktemp "$target.tmp.XXXXXX") || dot_die "Failed to stage $target"
    # mktemp creates mode 600; keep the existing mode, or use the umask for a new file.
    if ! { cp "$source" "$temporary" && chmod "$(dot_file_mode "$target")" "$temporary"; }; then
      rm -f "$temporary"
      dot_die "Failed to copy $2"
    fi
    if ! dot_backup "$target"; then
      rm -f "$temporary"
      dot_die "Failed to back up $target"
    fi
    if ! mv -f "$temporary" "$target"; then
      rm -f "$temporary"
      dot_die "Failed to replace $target"
    fi
    dot_ok "Updated ~/$1"
  fi

  case "$1" in
    .ssh/* | .aws/*) mode="${mode:-600}" ;;
  esac
  if [ -n "$mode" ]; then
    chmod "$mode" "$target" || dot_die "Failed to set mode on $target"
  fi
}

# Write stdin to a file atomically (used for state and generated config).
dot_write() {
  local target="$1" temporary
  mkdir -p "${target%/*}" || return 1
  temporary=$(mktemp "$target.tmp.XXXXXX") || return 1
  if cat > "$temporary" && mv -f "$temporary" "$target"; then
    return 0
  fi
  rm -f "$temporary"
  return 1
}

################################################################################
# State: upgrade throttle and applied-content markers
################################################################################

# True when an upgrade for KEY is due: forced, never recorded, unreadable, or old.
dot_due() {
  local stamp="$DOT_STATE/stamps/$1" last
  [ "$DOT_FORCE" = true ] && return 0
  [ -f "$stamp" ] || return 0
  last=$(cat "$stamp" 2>/dev/null)
  case "$last" in
    '' | *[!0-9]*) return 0 ;;
  esac
  [ $(( $(date +%s) - last )) -ge "$DOT_UPGRADE_INTERVAL" ]
}

# Record a successful upgrade. Call only after the checked operation succeeded.
dot_stamp() {
  date +%s | dot_write "$DOT_STATE/stamps/$1"
}

dot_stamp_age() {
  local stamp="$DOT_STATE/stamps/$1" last
  last=$(cat "$stamp" 2>/dev/null) || { printf 'never'; return; }
  case "$last" in
    '' | *[!0-9]*) printf 'never'; return ;;
  esac
  last=$(( $(date +%s) - last ))
  if [ "$last" -lt 3600 ]; then printf '%dm ago' $((last / 60))
  elif [ "$last" -lt 172800 ]; then printf '%dh ago' $((last / 3600))
  else printf '%dd ago' $((last / 86400))
  fi
}

# Applied markers record content that was applied successfully, so a failed
# application is retried and unchanged content is skipped.
dot_applied() {
  dot_same_file "$1" "$DOT_STATE/applied/$2"
}

dot_mark_applied() {
  dot_write "$DOT_STATE/applied/$2" < "$1"
}

################################################################################
# Environment
################################################################################

# Homebrew prefixes in lookup order; override for a custom prefix.
DOT_BREW_PREFIXES="${DOT_BREW_PREFIXES:-/opt/homebrew /home/linuxbrew/.linuxbrew /usr/local}"

# Make tools installed by earlier modules visible to later ones.
dot_load_paths() {
  local prefix
  for prefix in $DOT_BREW_PREFIXES; do
    if [ -x "$prefix/bin/brew" ]; then
      eval "$("$prefix/bin/brew" shellenv)"
      break
    fi
  done
  case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) PATH="$HOME/.local/bin:$PATH" ;;
  esac
  export PATH
}

# Machine-specific values (identifiers, hosts) live outside the repository.
dot_load_local_env() {
  if [ -f "$DOT_CONFIG/local.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$DOT_CONFIG/local.env"
    set +a
  fi
}

# Available memory in GiB on Linux (empty elsewhere).
dot_mem_available_gib() {
  awk '/^MemAvailable:/ { printf "%d\n", $2 / 1048576 }' "${DOT_SYSROOT:-}/proc/meminfo" 2>/dev/null
}
