# shellcheck shell=bash
# Zsh as the login shell, Oh My Zsh, the Dracula theme and shell startup files.

shell::describe() { printf 'Zsh, Oh My Zsh, Dracula theme, shell and editor startup files\n'; }
shell::status() { printf 'login shell %s\n' "${SHELL:-unknown}"; }

# Startup files: target (relative to $HOME) and source (relative to $DOT_HOME).
_shell_files() {
  printf '%s\n' \
    ".zshrc config/shell/zshrc" \
    ".bashrc config/shell/bashrc" \
    ".profile config/shell/profile" \
    ".aliases config/shell/aliases" \
    ".config/dotfiles/nvm.sh config/shell/nvm.sh" \
    ".vimrc config/vim/vimrc" \
    ".tmux.conf config/tmux/tmux.conf"
  if [ -f "$DOT_HOME/config/shell/zprofile/$DOT_OS.$DOT_ARCH.sh" ]; then
    printf '%s\n' ".zprofile config/shell/zprofile/$DOT_OS.$DOT_ARCH.sh"
  fi
}

# A failed Oh My Zsh install is moved aside so the next run can retry cleanly.
_shell_archive_omz() {
  local backup
  [ -e "$HOME/.oh-my-zsh" ] || [ -L "$HOME/.oh-my-zsh" ] || return 0
  backup=$(mktemp -d "$HOME/.oh-my-zsh.backup.XXXXXX") || return 1
  if mv "$HOME/.oh-my-zsh" "$backup/oh-my-zsh"; then
    dot_info "Preserved incomplete Oh My Zsh at $backup/oh-my-zsh"
  else
    rmdir "$backup"
    return 1
  fi
}

_shell_oh_my_zsh() {
  if [ -s "$HOME/.oh-my-zsh/oh-my-zsh.sh" ]; then
    if dot_due shell && [ -d "$HOME/.oh-my-zsh/.git" ]; then
      dot_run "Updating Oh My Zsh and Dracula"
      git -C "$HOME/.oh-my-zsh" pull -q --ff-only || dot_warn "Oh My Zsh update failed"
      [ ! -d "$HOME/.dracula/zsh/.git" ] || git -C "$HOME/.dracula/zsh" pull -q --ff-only ||
        dot_warn "Dracula theme update failed"
    fi
    return 0
  fi
  _shell_archive_omz || dot_die "Failed to move an incomplete Oh My Zsh aside"
  dot_run "Installing Oh My Zsh"
  if RUNZSH=no CHSH=no KEEP_ZSHRC=yes dot_install_script \
       https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh &&
     [ -s "$HOME/.oh-my-zsh/oh-my-zsh.sh" ]; then
    dot_ok "Oh My Zsh installed"
  else
    _shell_archive_omz
    dot_warn "Oh My Zsh installation failed; retried on the next run"
  fi
}

_shell_dracula() {
  if [ ! -d "$HOME/.dracula/zsh" ]; then
    mkdir -p "$HOME/.dracula"
    dot_retry "Clone Dracula" git clone -q https://github.com/dracula/zsh.git "$HOME/.dracula/zsh" ||
      { dot_warn "Failed to clone the Dracula theme"; return 0; }
  fi
  if [ -d "$HOME/.oh-my-zsh/themes" ] && [ ! -L "$HOME/.oh-my-zsh/themes/dracula.zsh-theme" ]; then
    ln -sf "$HOME/.dracula/zsh/dracula.zsh-theme" "$HOME/.oh-my-zsh/themes/dracula.zsh-theme"
  fi
}

_shell_login_zsh() {
  local zsh_path
  case "${SHELL:-}" in
    */zsh) return 0 ;;
  esac
  zsh_path=$(command -v zsh) || { dot_warn "zsh is not installed; the login shell is unchanged"; return 0; }
  grep -qx "$zsh_path" /etc/shells 2>/dev/null ||
    printf '%s\n' "$zsh_path" | dot_sudo tee -a /etc/shells >/dev/null
  dot_run "Changing the login shell to $zsh_path"
  if chsh -s "$zsh_path" 2>/dev/null || dot_sudo chsh -s "$zsh_path" "$(id -un)"; then
    dot_ok "Login shell is zsh (applies to new sessions)"
  else
    dot_warn "Failed to change the login shell to zsh"
  fi
}

shell::up() {
  local target source
  _shell_oh_my_zsh
  _shell_dracula
  while read -r target source; do
    dot_install_file "$target" "$source"
  done <<EOF
$(_shell_files)
EOF
  _shell_login_zsh
  dot_due shell && dot_stamp shell
  dot_ok "Shell startup files are current"
}
