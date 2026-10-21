# shellcheck shell=bash
# macOS terminal settings: iTerm2 Dracula colors and profile, Ghostty config.

terminal::describe() { printf 'iTerm2 and Ghostty settings with Dracula colors\n'; }
terminal::supported() { dot_platform_is macos; }

terminal::up() {
  local colors="$HOME/Library/Application Support/iTerm2/Dracula.itermcolors"
  if [ ! -d "$HOME/.dracula/iterm" ]; then
    dot_retry "Clone Dracula for iTerm2" git clone -q https://github.com/dracula/iterm.git "$HOME/.dracula/iterm" ||
      dot_warn "Failed to clone Dracula for iTerm2"
  fi
  if [ -f "$HOME/.dracula/iterm/Dracula.itermcolors" ] && [ ! -L "$colors" ]; then
    mkdir -p "${colors%/*}" && ln -sf "$HOME/.dracula/iterm/Dracula.itermcolors" "$colors"
  fi
  dot_install_file .iterm2/profiles.json config/terminal/iterm2-profiles.json
  dot_install_file .config/ghostty/config config/terminal/ghostty.config
  dot_ok "Terminal settings are current"
}
