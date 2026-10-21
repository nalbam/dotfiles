# shellcheck shell=bash
# Git base settings and the directory-specific identities included by them.

git::describe() { printf 'Git settings and directory-based identities\n'; }

git::status() { printf '%s <%s>\n' "$(git config --global user.name 2>/dev/null)" "$(git config --global user.email 2>/dev/null)"; }

# Every config/git/gitconfig-* file is deployed, so each includeIf target in
# the base gitconfig exists on every machine.
git::up() {
  local source name
  dot_install_file .gitconfig config/git/gitconfig
  for source in "$DOT_HOME"/config/git/gitconfig-*; do
    [ -f "$source" ] || continue
    name="${source##*/}"
    dot_install_file ".$name" "config/git/$name"
  done
  dot_ok "Git configuration is current"
}
