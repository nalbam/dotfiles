# shellcheck shell=bash
# Python command-line tools installed with pip (toast-cli).

DOT_PIP_PACKAGES="${DOT_PIP_PACKAGES:-toast-cli}"

python::describe() { printf 'pip tools: %s\n' "$DOT_PIP_PACKAGES"; }
python::supported() { dot_has python3; }
python::status() { toast --version 2>/dev/null | head -1 || printf 'toast not installed\n'; }

# PEP 668 systems refuse plain installs, and some machines lock the user site;
# try each method in order and stop at the first that works.
python_pip_install() {
  python3 -m pip install "$@" >/dev/null 2>&1 ||
    python3 -m pip install --user "$@" >/dev/null 2>&1 ||
    python3 -m pip install --break-system-packages --user "$@" >/dev/null 2>&1 ||
    sudo python3 -m pip install "$@" >/dev/null 2>&1
}

python::up() {
  local package ok=true
  if dot_has toast && ! dot_due python; then
    dot_skip "pip tools checked $(dot_stamp_age python)"
    return 0
  fi
  for package in $DOT_PIP_PACKAGES; do
    dot_run "pip install --upgrade $package"
    if python_pip_install --upgrade "$package"; then
      dot_ok "$package is current"
    else
      dot_warn "Failed to install $package with every pip method"
      ok=false
    fi
  done
  [ "$ok" = true ] && dot_stamp python
  return 0
}
