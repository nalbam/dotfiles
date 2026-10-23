# shellcheck shell=bash
# Directories, SSH key and credential templates.
#
# The CLI stays at $DOT_HOME/bin/dot and is not put on PATH: `dot` belongs to
# Graphviz and other tools, and a machine's existing commands must keep working.

base::describe() { printf 'Directories, SSH key, SSH/AWS templates\n'; }

# Markers from the previous installer (~/.toast) keep their meaning, so an
# existing machine does not repeat work such as macOS preferences.
_base_migrate_legacy_state() {
  local name key
  [ -d "$HOME/.toast" ] || return 0
  if [ -f "$HOME/.toast/macos.applied" ] && [ ! -f "$DOT_STATE/applied/macos-defaults" ]; then
    dot_write "$DOT_STATE/applied/macos-defaults" < "$HOME/.toast/macos.applied"
  fi
  for name in brew claude pip; do
    key="$name"
    [ "$name" = pip ] && key=python
    if [ -f "$HOME/.toast/last_update_$name" ] && [ ! -f "$DOT_STATE/stamps/$key" ]; then
      dot_write "$DOT_STATE/stamps/$key" < "$HOME/.toast/last_update_$name"
    fi
  done
  if [ -f "$HOME/.Brewfile" ] && [ ! -f "$DOT_STATE/applied/Brewfile" ]; then
    dot_write "$DOT_STATE/applied/Brewfile" < "$HOME/.Brewfile"
  fi
}

base::up() {
  mkdir -p "$HOME/.ssh" "$HOME/.aws" "$HOME/.local/bin" "$DOT_CONFIG" "$DOT_STATE" ||
    dot_die "Failed to create base directories"
  # ssh refuses keys and config in a group- or world-readable ~/.ssh.
  chmod 700 "$HOME/.ssh" || dot_die "Failed to protect ~/.ssh"
  _base_migrate_legacy_state

  if [ ! -f "$HOME/.ssh/id_ed25519" ]; then
    if ssh-keygen -q -t ed25519 -f "$HOME/.ssh/id_ed25519" -N '' -C "$(id -un)@$(hostname -s 2>/dev/null || hostname)"; then
      dot_ok "Generated ~/.ssh/id_ed25519"
    else
      dot_warn "Failed to generate an ED25519 SSH key"
    fi
  fi

  # Templates are copied once; machines usually replace them with private files.
  [ -f "$HOME/.ssh/config" ] || dot_install_file .ssh/config config/ssh/config
  [ -f "$HOME/.aws/config" ] || dot_install_file .aws/config config/aws/config

  # Earlier versions linked ~/.local/bin/dot here. Remove only that link.
  if [ -L "$HOME/.local/bin/dot" ] && [ "$(readlink "$HOME/.local/bin/dot")" = "$DOT_HOME/bin/dot" ]; then
    rm -f "$HOME/.local/bin/dot" || dot_die "Failed to remove ~/.local/bin/dot"
    dot_ok "Removed the ~/.local/bin/dot link"
  fi
  dot_ok "Base directories ready"
}
