# shellcheck shell=bash
# Neovim configuration (config/nvim/nvim -> ~/.config/nvim).

nvim::describe() { printf 'Neovim configuration\n'; }
nvim::status() { nvim --version 2>/dev/null | head -1 || printf 'nvim not installed\n'; }

# The configuration directory is replaced as a whole when it differs. The
# previous directory is kept as ~/.config/nvim.bak-<time>.
nvim::up() {
  local source="$DOT_HOME/config/nvim/nvim" target="$HOME/.config/nvim" backup
  [ -d "$source" ] || dot_die "Missing source: config/nvim/nvim"
  if [ -d "$target" ] && diff -qr "$source" "$target" >/dev/null 2>&1; then
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
    dot_ok "Installed ~/.config/nvim"
  fi
  dot_has nvim || dot_warn "nvim is not installed; install Neovim to use this configuration"
}
