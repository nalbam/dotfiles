#!/bin/bash
# Bootstrap: make sure ~/.dotfiles exists, then hand over to `dot up`.
#
#   curl -fsSL https://nalbam.github.io/dotfiles/run.sh | bash
#   bash ~/.dotfiles/run.sh [--force] [--vibe]
#
# The braces make Bash read the whole file before running it, so a checkout
# update cannot change this script while it executes.
{

DOT_HOME="${DOT_HOME:-$HOME/.dotfiles}"
DOT_REPO_URL="${DOT_REPO_URL:-https://github.com/nalbam/dotfiles.git}"
DOT_ARCHIVE_URL="${DOT_ARCHIVE_URL:-https://codeload.github.com/nalbam/dotfiles/tar.gz/refs/heads/main}"

usage() {
  printf '%s\n' \
    'Usage: bash run.sh [--force] [--vibe] [--help]' \
    '  (no options)  Install or upgrade this machine (runs `dot up`).' \
    '  --force       Upgrade even when the last upgrade was less than 6 hours ago.' \
    '  --vibe        Deploy AI tool settings only (runs `dot vibe`).' \
    '  -h, --help    Show this help without changing files.'
}

fail() {
  printf '\n  ✗ %s\n\n' "$*" >&2
  exit 1
}

COMMAND=up
ARGS=""
for arg in "$@"; do
  case "$arg" in
    --vibe) COMMAND=vibe ;;
    --force) ARGS="--force" ;;
    -h | --help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$arg" >&2; usage >&2; exit 2 ;;
  esac
done

retry() {
  local attempt=1 wait_time=5
  while :; do
    "$@" && return 0
    [ "$attempt" -lt 3 ] || return 1
    printf '  ℹ Retrying in %ss (attempt %s/3)\n' "$wait_time" "$attempt"
    sleep "$wait_time"
    attempt=$((attempt + 1))
    wait_time=$((wait_time * 2))
  done
}

# The macOS /usr/bin/git stub opens a GUI installer without Command Line Tools.
git_usable() {
  command -v git >/dev/null 2>&1 || return 1
  if [ "$(uname -s)" = Darwin ] && [ "$(command -v git)" = /usr/bin/git ]; then
    xcode-select -p >/dev/null 2>&1 || return 1
  fi
}

# Without Git, install from the archive; `dot up` converts it to a checkout later.
install_archive() {
  local staging
  staging=$(mktemp -d "${DOT_HOME%/*}/.dotfiles.download.XXXXXX") || return 1
  if retry curl -fsSL --connect-timeout 10 -o "$staging/main.tar.gz" "$DOT_ARCHIVE_URL" &&
     mkdir "$staging/tree" &&
     tar -xzf "$staging/main.tar.gz" -C "$staging/tree" --strip-components 1 &&
     [ -x "$staging/tree/bin/dot" ] &&
     mv "$staging/tree" "$DOT_HOME"; then
    rm -rf "$staging"
    return 0
  fi
  rm -rf "$staging"
  return 1
}

if [ ! -x "$DOT_HOME/bin/dot" ]; then
  if [ -d "$DOT_HOME/.git" ]; then
    # A checkout from before `dot` existed: update it in place.
    printf '  → Updating %s\n' "$DOT_HOME"
    git_usable && retry git -C "$DOT_HOME" pull --ff-only ||
      fail "Could not update $DOT_HOME. Check: git -C $DOT_HOME status"
  elif [ -e "$DOT_HOME" ]; then
    fail "$DOT_HOME exists but is not a dotfiles checkout. Move it aside and run again."
  elif git_usable; then
    printf '  → Cloning %s\n' "$DOT_REPO_URL"
    retry git clone -q "$DOT_REPO_URL" "$DOT_HOME" || fail "Clone failed: $DOT_REPO_URL"
  else
    printf '  → Downloading dotfiles (Git is not usable yet)\n'
    install_archive || fail "Download failed: $DOT_ARCHIVE_URL"
  fi
fi

[ -x "$DOT_HOME/bin/dot" ] || fail "$DOT_HOME/bin/dot is missing after the update."

# With `curl | bash`, stdin is the finished download. Give prompts the terminal.
if [ ! -t 0 ] && (exec < /dev/tty) 2>/dev/null; then
  exec < /dev/tty
fi

if [ "$COMMAND" = vibe ]; then
  exec /bin/bash "$DOT_HOME/bin/dot" vibe
fi
# shellcheck disable=SC2086
exec /bin/bash "$DOT_HOME/bin/dot" up $ARGS

}
