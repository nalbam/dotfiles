# shellcheck shell=bash
# Claude Code (native installer); upgraded with `claude update`.

claude::describe() { printf 'Claude Code CLI\n'; }
# The native build is published for 64-bit macOS and Linux.
claude::supported() { case "$DOT_ARCH" in x86_64 | arm64 | aarch64) return 0 ;; esac; return 1; }
claude::detect() { dot_has claude; }
claude::status() { if dot_has claude; then claude --version 2>/dev/null | head -1; else printf 'not installed\n'; fi; }

claude::up() {
  if ! dot_has claude; then
    dot_run "Installing Claude Code"
    dot_install_script https://claude.ai/install.sh || dot_die "Claude Code installation failed"
    dot_load_paths
    dot_has claude || dot_die "Claude Code installed but claude is not on PATH"
    dot_stamp claude
    dot_ok "Installed $(claude --version 2>/dev/null | head -1)"
    return 0
  fi
  if ! dot_due claude; then
    dot_skip "Checked $(dot_stamp_age claude)"
    return 0
  fi
  dot_run "claude update"
  if claude update; then
    dot_stamp claude
  else
    dot_warn "claude update failed; retried on the next run"
  fi
}
