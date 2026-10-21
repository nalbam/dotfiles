# shellcheck shell=bash
# VibeMon summary collector as a systemd user service (DGX Spark).
. "$DOT_HOME/lib/spark.sh"

VIBEMON_UNIT="dockpad-vibemon-collector.service"
VIBEMON_FILES="vibemon.env scripts/setup-vibemon.sh scripts/check-vibemon.sh"

vibemon::describe() { printf 'VibeMon summary collector (systemd user service)\n'; }
vibemon::supported() { spark_supported; }
vibemon::detect() { [ -f "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/$VIBEMON_UNIT" ]; }

vibemon::status() {
  systemctl --user is-active "$VIBEMON_UNIT" 2>/dev/null || printf 'inactive\n'
}

# The collector revision is pinned in stacks/dgx-spark/vibemon.env. Setup needs
# ~/.config/vibemon/collector.env with VIBEMON_WRITE_TOKEN (mode 600) and
# systemd lingering for the user; the script reports what is missing.
vibemon::up() {
  if spark_marked vibemon $VIBEMON_FILES && systemctl --user is-active --quiet "$VIBEMON_UNIT" 2>/dev/null &&
     [ "${DOT_ADDING:-}" != true ]; then
    dot_skip "Collector is active and matches the repository"
    return 0
  fi
  if spark_adoptable vibemon $VIBEMON_FILES && systemctl --user is-active --quiet "$VIBEMON_UNIT" 2>/dev/null &&
     [ "${DOT_ADDING:-}" != true ]; then
    spark_mark vibemon $VIBEMON_FILES
    dot_ok "Adopted the active collector"
    return 0
  fi
  spark_sync $VIBEMON_FILES || dot_die "Failed to copy the collector files into $DOT_SPARK_DIR"
  spark_script setup-vibemon.sh || dot_die "Collector setup failed"
  spark_mark vibemon $VIBEMON_FILES
  dot_ok "Collector is active"
}
