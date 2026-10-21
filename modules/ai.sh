# shellcheck shell=bash
# AI tool settings for Claude Code, Codex, OpenCode and Kiro (scripts/sync-ai-tools.py).

ai::describe() { printf 'Claude Code, Codex, OpenCode and Kiro settings\n'; }

ai::up() {
  python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null ||
    dot_die "AI settings need Python 3.11 or newer (python3: $(python3 --version 2>&1))"
  python3 "$DOT_HOME/scripts/sync-ai-tools.py" ||
    dot_die "AI settings sync failed; review the error above"
}
