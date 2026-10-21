# shellcheck shell=bash
# Node.js through nvm. The default is the newest Node.js $DOT_NODE_VERSION.

DOT_NODE_VERSION="${DOT_NODE_VERSION:-24}"
DOT_NVM_VERSION="${DOT_NVM_VERSION:-v0.40.3}"

node::describe() { printf 'nvm and Node.js %s as the default\n' "$DOT_NODE_VERSION"; }
node::detect() { [ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]; }
node::status() { node --version 2>/dev/null || printf 'not installed\n'; }

_node_load() {
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  mkdir -p "$NVM_DIR" || return 1
  # shellcheck disable=SC1091
  . "$DOT_HOME/config/shell/nvm.sh"
  dot_fn nvm
}

node::up() {
  if ! _node_load; then
    # Without Homebrew (servers, Raspberry Pi), use the upstream installer
    # without editing shell startup files; config/shell/nvm.sh loads it.
    dot_run "Installing nvm $DOT_NVM_VERSION"
    PROFILE=/dev/null dot_install_script "https://raw.githubusercontent.com/nvm-sh/nvm/$DOT_NVM_VERSION/install.sh" ||
      dot_die "nvm installation failed"
    _node_load || dot_die "nvm is installed but could not be loaded"
  fi

  if [ "$(nvm version "$DOT_NODE_VERSION")" != N/A ] && ! dot_due node; then
    dot_skip "Node.js $(nvm version "$DOT_NODE_VERSION") checked $(dot_stamp_age node)"
    return 0
  fi

  # `nvm install` resolves the newest release of the major version, so the same
  # command installs and upgrades. Source builds (no prebuilt binary) are slow.
  dot_run "nvm install $DOT_NODE_VERSION"
  nvm install "$DOT_NODE_VERSION" >/dev/null || dot_die "nvm install $DOT_NODE_VERSION failed"
  nvm alias default "$DOT_NODE_VERSION" >/dev/null && nvm use default >/dev/null ||
    dot_die "Failed to select Node.js $DOT_NODE_VERSION as the default"
  . "$DOT_HOME/config/shell/nvm.sh"
  case "$(node --version 2>/dev/null)" in
    "v$DOT_NODE_VERSION".*) ;;
    *) dot_die "Node.js $DOT_NODE_VERSION was selected, but node resolves to $(command -v node): $(node --version 2>/dev/null || printf unavailable)" ;;
  esac
  dot_stamp node
  dot_ok "Node.js $(node --version) is the default"
}
