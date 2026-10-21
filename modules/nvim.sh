# shellcheck shell=bash
# Neovim configuration (config/nvim/nvim -> ~/.config/nvim).

nvim::describe() { printf 'Neovim configuration\n'; }
nvim::status() { nvim --version 2>/dev/null | head -1 || printf 'nvim not installed\n'; }

# Digest of the repository configuration (file names and contents).
_nvim_digest() {
  local list
  list=$(mktemp "${TMPDIR:-/tmp}/dot-nvim.XXXXXX") || return 1
  (cd "$DOT_HOME/config/nvim/nvim" && find . -type f | LC_ALL=C sort | while IFS= read -r file; do
    printf '%s %s\n' "$(dot_md5 "$file")" "$file"
  done) > "$list"
  dot_md5 "$list"
  rm -f "$list"
}

# The configuration is installed when it is missing or when the repository
# version changed since the last install. Neovim writes lazy-lock.json and
# plugin state into ~/.config/nvim, so local differences alone do not trigger a
# reinstall. A replaced configuration is kept as ~/.config/nvim.bak-<time>.
nvim::up() {
  local source="$DOT_HOME/config/nvim/nvim" target="$HOME/.config/nvim" marker digest backup
  [ -d "$source" ] || dot_die "Missing source: config/nvim/nvim"
  marker="$DOT_STATE/applied/nvim"
  digest=$(_nvim_digest) || dot_die "Failed to read config/nvim/nvim"
  if [ -d "$target" ] && [ "$(cat "$marker" 2>/dev/null)" = "$digest" ]; then
    dot_skip "Configuration is current"
  else
    mkdir -p "$HOME/.config" || dot_die "Failed to create ~/.config"
    if [ -e "$target" ] || [ -L "$target" ]; then
      backup="$target.bak-$(date +%Y%m%d-%H%M%S)"
      while [ -e "$backup" ] || [ -L "$backup" ]; do backup="$backup.1"; done
      mv "$target" "$backup" || dot_die "Failed to move $target aside"
      dot_info "Previous configuration: $backup"
    fi
    cp -R "$source" "$target" || dot_die "Failed to copy the Neovim configuration"
    printf '%s\n' "$digest" | dot_write "$marker" || dot_die "Failed to record the Neovim configuration"
    dot_ok "Installed ~/.config/nvim"
  fi
  dot_has nvim || dot_warn "nvim is not installed; install Neovim to use this configuration"
}
