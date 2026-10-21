# shellcheck shell=bash
# `dot @HOST ...` runs dot on another machine over SSH.
#
# HOST is either a name with $DOT_CONFIG/hosts/<name>.env or an SSH destination
# (an alias from ~/.ssh/config or user@host). A hosts file is not part of the
# repository because it identifies a private machine:
#
#   DOT_HOST=spark-01.example.ts.net   # required
#   DOT_USER=me                        # optional
#   DOT_IDENTITY=~/.ssh/id_ed25519     # optional
#   DOT_SSH_OPTIONS="-p 2222"          # optional, split on spaces

DOT_BOOTSTRAP_URL="${DOT_BOOTSTRAP_URL:-https://nalbam.github.io/dotfiles/run.sh}"

dot_remote() {
  local name="$1" file destination command arg identity
  shift
  [ -n "$name" ] || { dot_echo "  ✗ Usage: dot @HOST COMMAND..." 1 >&2; return 2; }
  case "$name" in
    *[!A-Za-z0-9@._-]*) dot_echo "  ✗ Invalid host: $name" 1 >&2; return 2 ;;
  esac

  file="$DOT_CONFIG/hosts/$name.env"
  DOT_HOST="" DOT_USER="" DOT_IDENTITY="" DOT_SSH_OPTIONS=""
  if [ -f "$file" ]; then
    # shellcheck disable=SC1090
    . "$file" || return 1
    [ -n "$DOT_HOST" ] || { dot_echo "  ✗ DOT_HOST is missing in $file" 1 >&2; return 2; }
    destination="$DOT_HOST"
    [ -z "$DOT_USER" ] || destination="$DOT_USER@$DOT_HOST"
  else
    destination="$name"
  fi

  local ssh_args=(-o ConnectTimeout=10)
  [ -t 0 ] && [ -t 1 ] && ssh_args+=(-t) || ssh_args+=(-T)
  # shellcheck disable=SC2206
  [ -z "$DOT_SSH_OPTIONS" ] || ssh_args+=($DOT_SSH_OPTIONS)
  if [ -n "$DOT_IDENTITY" ]; then
    identity="${DOT_IDENTITY/#\~/$HOME}"
    [ -r "$identity" ] || { dot_echo "  ✗ SSH identity is not readable: $identity" 1 >&2; return 2; }
    ssh_args+=(-o IdentitiesOnly=yes -i "$identity")
  fi

  if [ "${1:-}" = bootstrap ]; then
    command="curl -fsSL $(printf '%q' "$DOT_BOOTSTRAP_URL") | bash"
  else
    [ $# -gt 0 ] || set -- status
    # The remote login shell may be zsh or bash; %q output is valid in both.
    command='"$HOME/.dotfiles/bin/dot"'
    for arg in "$@"; do
      command="$command $(printf '%q' "$arg")"
    done
  fi
  exec ssh "${ssh_args[@]}" "$destination" "$command"
}
