# shellcheck shell=bash
# Homebrew and the platform Brewfile (packages/Brewfile.darwin|linux).

brew::describe() { printf 'Homebrew and packages/Brewfile.%s\n' "$DOT_OS"; }

# Homebrew does not support 32-bit ARM Linux.
brew::supported() { [ "$DOT_ARCH" != armv7l ] && [ "$DOT_ARCH" != armv6l ]; }
brew::detect() { dot_has brew; }
brew::status() { if dot_has brew; then brew --version | head -1; else printf 'not installed\n'; fi; }

_brew_install() {
  dot_run "Installing Homebrew"
  if ! dot_install_script https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh; then
    dot_die "Homebrew installation failed; review the error above"
  fi
  dot_load_paths
  dot_has brew || dot_die "Homebrew installer finished but brew is not on PATH"
  dot_ok "Homebrew installed"
}

# On DGX Spark, model serving shares memory with the host and a watchdog stops
# Flash when memory runs low. Source builds during an upgrade can trigger it.
_brew_memory_ok() {
  local available
  dot_platform_is dgx-spark || return 0
  available=$(dot_mem_available_gib)
  [ -n "$available" ] || return 0
  if [ "$available" -lt "${DOT_BREW_MIN_MEMORY_GIB:-16}" ]; then
    dot_warn "Only ${available}GiB memory available; skipped Homebrew upgrades to protect model serving (set DOT_BREW_MIN_MEMORY_GIB to change)"
    return 1
  fi
}

brew::up() {
  local brewfile="$DOT_HOME/packages/Brewfile.$DOT_OS" due=false changed=false ok=true
  dot_has brew || _brew_install

  dot_due brew && due=true
  if [ -f "$brewfile" ]; then
    # A failed checksum is neither "applied" nor a reason to apply.
    dot_applied "$brewfile" Brewfile
    case $? in
      0) ;;
      2) dot_die "Failed to compare the Brewfile with its completion marker" ;;
      *) changed=true ;;
    esac
  fi
  if [ "$due" = false ] && [ "$changed" = false ]; then
    dot_skip "Packages upgraded $(dot_stamp_age brew); next upgrade after 6 hours (dot up --force)"
    return 0
  fi
  _brew_memory_ok || return 0

  if [ "$due" = true ]; then
    dot_run "brew update && brew upgrade"
    if ! { brew update && brew upgrade; }; then
      dot_warn "brew update/upgrade failed"
      ok=false
    fi
  fi
  if [ -f "$brewfile" ]; then
    dot_run "brew bundle --file=packages/Brewfile.$DOT_OS"
    if brew bundle --file="$brewfile"; then
      dot_mark_applied "$brewfile" Brewfile
    else
      dot_warn "brew bundle failed; some packages are missing"
      ok=false
    fi
  fi
  brew cleanup >/dev/null 2>&1 || true
  # Stamp only a complete upgrade so a failure is retried on the next run.
  if [ "$due" = true ] && [ "$ok" = true ]; then
    dot_stamp brew
  fi
  [ "$ok" = true ] && dot_ok "Homebrew packages are current"
  return 0
}
