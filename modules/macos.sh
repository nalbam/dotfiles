# shellcheck shell=bash
# macOS: Command Line Tools, Rosetta 2, key bindings and system preferences.

macos::describe() { printf 'Command Line Tools, Rosetta 2, key bindings, preferences\n'; }
macos::supported() { dot_platform_is macos; }
macos::status() { sw_vers -productVersion 2>/dev/null; }

macos::up() {
  if ! xcode-select -p >/dev/null 2>&1; then
    dot_run "Starting the Command Line Tools installer"
    xcode-select --install >/dev/null 2>&1 || true
    dot_warn "Complete the Command Line Tools dialog, then run dot up again"
  fi

  if [ "$DOT_ARCH" = arm64 ] && ! pgrep -q oahd; then
    dot_run "Installing Rosetta 2"
    sudo softwareupdate --install-rosetta --agree-to-license >/dev/null || dot_warn "Rosetta 2 installation failed"
  fi

  # The key binding (₩ types `) is copied once so local edits survive.
  if [ ! -f "$HOME/Library/KeyBindings/DefaultkeyBinding.dict" ]; then
    dot_install_file Library/KeyBindings/DefaultkeyBinding.dict config/macos/DefaultkeyBinding.dict
  fi

  # Preferences are applied when their script changed or the last attempt
  # failed. A failed checksum is neither "applied" nor a reason to re-apply.
  local applied
  dot_applied "$DOT_HOME/config/macos/defaults.sh" macos-defaults
  applied=$?
  if [ "$applied" -eq 0 ]; then
    dot_skip "System preferences already applied"
  elif [ "$applied" -eq 2 ]; then
    dot_die "Failed to compare system preferences with their completion marker"
  else
    dot_run "Applying system preferences (config/macos/defaults.sh)"
    if ! /bin/bash "$DOT_HOME/config/macos/defaults.sh"; then
      dot_warn "System preferences failed; they are retried on the next run"
    elif dot_mark_applied "$DOT_HOME/config/macos/defaults.sh" macos-defaults; then
      dot_ok "System preferences applied; some take effect after logout"
    else
      dot_warn "System preferences applied but not recorded; they are applied again on the next run"
    fi
  fi
}

# dot upgrade-system on macOS: lists updates; installs them only with --yes.
macos::system_upgrade() {
  if [ "$1" != true ]; then
    softwareupdate --list
    dot_info "Nothing changed. Run 'dot upgrade-system --yes' to install recommended updates."
    return 0
  fi
  sudo softwareupdate --install --recommended || return 1
  dot_ok "Recommended updates installed; restart if macOS asks for it"
}
