# shellcheck shell=bash
# Grafana Alloy and DCGM Exporter on DGX Spark, shipping metrics to Grafana Cloud.
. "$DOT_HOME/lib/spark.sh"

# Files whose change requires the monitoring setup to run again.
MONITORING_FILES="grafana/ scripts/setup-grafana.sh docker-compose.yml"

monitoring::describe() { printf 'Grafana Alloy + DCGM Exporter to Grafana Cloud (DGX Spark)\n'; }
monitoring::supported() { spark_supported; }
monitoring::detect() { [ -s "$DOT_SPARK_DIR/.env.grafana" ]; }

monitoring::status() {
  if [ -s "$DOT_SPARK_DIR/.env.grafana" ]; then printf 'configured\n'; else printf 'not configured\n'; fi
}

# The first setup asks for the Grafana Cloud token and stores it in the runtime
# .env.grafana (mode 600). Later deployments of the llm stack include the
# monitoring profile automatically while that file exists.
monitoring::up() {
  if [ -s "$DOT_SPARK_DIR/.env.grafana" ] && spark_marked monitoring $MONITORING_FILES && [ "$DOT_FORCE" != true ]; then
    dot_skip "Monitoring matches the repository"
    return 0
  fi
  # A host set up before dot keeps running untouched when its files already match.
  if [ -s "$DOT_SPARK_DIR/.env.grafana" ] && spark_in_sync $MONITORING_FILES && [ "$DOT_FORCE" != true ]; then
    spark_mark monitoring $MONITORING_FILES
    dot_ok "Adopted the existing monitoring setup"
    return 0
  fi
  spark_sync || dot_die "Failed to copy the stack into $DOT_SPARK_DIR"
  if [ ! -s "$DOT_SPARK_DIR/.env.grafana" ] && [ ! -t 0 ] && [ -z "${GCLOUD_RW_API_KEY:-}" ]; then
    dot_die "First setup needs a terminal for the Grafana Cloud token (or GCLOUD_RW_API_KEY). Run: dot add monitoring"
  fi
  spark_script setup-grafana.sh || dot_die "Monitoring setup failed; see the Alloy and DCGM logs above"
  spark_mark monitoring $MONITORING_FILES
  dot_ok "Alloy and DCGM Exporter are ready"
}
