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

# scripts/setup-grafana.sh asks for missing Grafana Cloud values on a terminal,
# stores them in the runtime .env.grafana (mode 600) and starts Alloy and DCGM
# Exporter. Later deployments of the llm stack include the monitoring profile
# while that file exists. Alloy and DCGM Exporter restart during setup; model
# serving does not.
monitoring::up() {
  local missing
  if [ ! -f "$DOT_SPARK_DIR/.env" ]; then
    dot_die "Monitoring runs inside the model stack; deploy it first: dot add llm"
  fi
  if [ -s "$DOT_SPARK_DIR/.env.grafana" ] && spark_marked monitoring $MONITORING_FILES &&
     [ "${DOT_ADDING:-}" != true ]; then
    dot_skip "Monitoring matches the repository"
    return 0
  fi
  # A host set up before dot keeps running untouched when its files already match.
  if [ -s "$DOT_SPARK_DIR/.env.grafana" ] && spark_adoptable monitoring $MONITORING_FILES &&
     [ "${DOT_ADDING:-}" != true ]; then
    spark_mark monitoring $MONITORING_FILES
    dot_ok "Adopted the existing monitoring setup"
    return 0
  fi
  # Copying a new config.alloy before its values exist would break Alloy on its
  # next restart, so check first and keep the running files when values are missing.
  missing=$(spark_grafana_missing | tr '\n' ' ')
  if [ -n "$missing" ] && [ ! -t 0 ]; then
    dot_die "Grafana Cloud values are missing ($missing); run on a terminal: dot add monitoring"
  fi
  spark_sync $MONITORING_FILES || dot_die "Failed to copy the monitoring files into $DOT_SPARK_DIR"
  spark_script setup-grafana.sh || dot_die "Monitoring setup failed; see the Alloy and DCGM logs above"
  spark_mark monitoring $MONITORING_FILES
  dot_ok "Alloy and DCGM Exporter are ready"
}
