# shellcheck shell=bash
# DGX Spark model serving: vLLM models, TensorFold Flash or ComfyUI via Docker Compose.
. "$DOT_HOME/lib/spark.sh"

llm::describe() { printf 'DGX Spark model serving stack (vLLM, Flash, ComfyUI)\n'; }
llm::supported() { spark_supported; }
llm::detect() { [ -f "$DOT_SPARK_DIR/.env" ]; }

llm::status() {
  if [ -f "$DOT_SPARK_DIR/.env" ]; then
    printf 'mode=%s dir=%s\n' "$(spark_mode)" "$DOT_SPARK_DIR"
  else
    printf 'not deployed\n'
  fi
}

_llm_deploy() {
  spark_sync || dot_die "Failed to copy the stack into $DOT_SPARK_DIR"
  dot_run "Deploying ${ONLY:-all services} (mode: $(spark_mode || true))"
  spark_script deploy.sh || return 1
  HEALTH_WAIT_SECONDS="${HEALTH_WAIT_SECONDS:-1800}" spark_script health-check.sh || return 1
}

# A routine dot up never redeploys a running stack: a deployment pulls images,
# starts preparation containers next to the serving ones and may recreate
# them. It deploys only the first time (no runtime .env yet) and on `dot add
# llm`; a changed stack on a deployed host is reported and left to
# `dot llm deploy`, which the operator runs when serving may be interrupted.
# Models and images are pinned in the runtime .env.
llm::up() {
  if [ ! -f "$DOT_SPARK_DIR/.env" ] || [ "${DOT_ADDING:-}" = true ]; then
    _llm_deploy || dot_die "Deployment failed; the previous containers keep running where possible"
    spark_mark llm
    dot_ok "Stack deployed (mode: $(spark_mode))"
  elif spark_marked llm; then
    dot_skip "Stack matches the repository (mode: $(spark_mode))"
  elif spark_adoptable llm; then
    spark_mark llm
    dot_ok "Adopted the running stack; files already match (mode: $(spark_mode))"
  else
    dot_warn "The repository changed the model stack; deploy it when serving may restart: dot llm deploy"
  fi
}

_llm_service() {
  case "${1:-}" in
    '' | *[!a-z0-9-]*) dot_echo "  ✗ Invalid service name: ${1:-}" 1 >&2; return 2 ;;
  esac
  spark_script compose.sh has-service "$1" || { dot_echo "  ✗ Unknown service: $1" 1 >&2; return 2; }
}

llm::cli() {
  local action="${1:-help}"
  [ $# -eq 0 ] || shift
  if [ "$action" != help ] && ! llm::supported; then
    dot_echo "  ✗ dot llm runs on a DGX Spark. From another machine use: dot @HOST llm $action" 1 >&2
    return 2
  fi
  case "$action" in
    deploy)
      if [ -n "${1:-}" ]; then _llm_service "$1" || return; fi
      ONLY="${1:-}" _llm_deploy || return
      # A single-service deploy leaves the other services on their previous definition.
      [ -n "${1:-}" ] || spark_mark llm
      ;;
    recreate)
      # Apply runtime .env changes that need no new image or model download (for
      # example a context length). A new model or image pin needs `dot llm deploy`.
      if [ -n "${1:-}" ]; then _llm_service "$1" || return; fi
      ONLY="${1:-}" SKIP_PULL=true FORCE_RECREATE=true _llm_deploy
      ;;
    mode)
      case "${1:-}" in
        models | flash | comfyui) ;;
        *) dot_echo "  ✗ Usage: dot llm mode models|flash|comfyui" 1 >&2; return 2 ;;
      esac
      spark_sync && spark_script switch-mode.sh "$1"
      ;;
    status) spark_script compose.sh ps "$@" ;;
    logs) spark_script compose.sh logs "$@" ;;
    config) spark_script compose.sh config "$@" ;;
    health) spark_script health-check.sh ;;
    public-api) spark_sync && spark_script setup-public-api.sh ;;
    start | stop | restart)
      _llm_service "${1:-}" || return
      spark_script compose.sh service "$action" "$1"
      ;;
    help | -h | --help)
      cat <<'EOF'
Usage: dot llm COMMAND

  deploy [SERVICE]       Copy the stack, pull and prepare pinned images and
                         models, deploy, and wait for health checks
  recreate [SERVICE]     Recreate containers after a runtime .env change that
                         needs no download (use deploy for a new model or image)
  mode models|flash|comfyui
                         Switch the serving mode (rolls back when unhealthy)
  status                 Show Compose services
  logs [ARGS...]         Show Compose logs (for example: logs -f llm)
  health                 Check containers and model endpoints
  config                 Render the Compose configuration
  public-api             Publish the key-protected API through Tailscale Funnel
  start|stop|restart SERVICE
EOF
      printf '\nRuntime directory: %s\n' "$DOT_SPARK_DIR"
      ;;
    *) dot_echo "  ✗ Unknown llm command: $action (see dot llm help)" 1 >&2; return 2 ;;
  esac
}
