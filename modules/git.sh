# shellcheck shell=bash
# Git base settings, the directory-specific identities included by them, and
# the global ignore file Git reads when core.excludesFile is unset.

git::describe() { printf 'Git settings, directory-based identities and global ignore\n'; }

git::status() { printf '%s <%s>\n' "$(git config --global user.name 2>/dev/null)" "$(git config --global user.email 2>/dev/null)"; }

# Git reads $XDG_CONFIG_HOME/git/ignore (default ~/.config/git/ignore) while
# core.excludesFile is unset. dot_install_file targets paths under $HOME only.
git::install_ignore() {
  local config="${XDG_CONFIG_HOME:-$HOME/.config}"
  case "$config" in
    "$HOME"/*) dot_install_file "${config#"$HOME"/}/git/ignore" config/git/ignore ;;
    *) dot_warn "XDG_CONFIG_HOME is outside HOME; install config/git/ignore to $config/git/ignore manually" ;;
  esac
}

# Every config/git/gitconfig-* file is deployed, so each includeIf target in
# the base gitconfig exists on every machine.
git::up() {
  local source name
  dot_install_file .gitconfig config/git/gitconfig
  git::install_ignore
  for source in "$DOT_HOME"/config/git/gitconfig-*; do
    [ -f "$source" ] || continue
    name="${source##*/}"
    dot_install_file ".$name" "config/git/$name"
  done
  dot_ok "Git configuration is current"
}
