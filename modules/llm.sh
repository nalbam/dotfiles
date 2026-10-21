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

# Applies the stack when the repository changed it (or with --force). Models and
# images are pinned in the runtime .env, so an unchanged stack has nothing to upgrade.
llm::up() {
  if [ -f "$DOT_SPARK_DIR/.env" ] && spark_marked llm && [ "$DOT_FORCE" != true ]; then
    dot_skip "Stack matches the repository (mode: $(spark_mode))"
    return 0
  fi
  if [ -f "$DOT_SPARK_DIR/.env" ] && spark_in_sync && [ "$DOT_FORCE" != true ]; then
    spark_mark llm
    dot_ok "Adopted the running stack; files already match (mode: $(spark_mode))"
    return 0
  fi
  _llm_deploy || dot_die "Deployment failed; the previous containers keep running where possible"
  spark_mark llm
  dot_ok "Stack deployed (mode: $(spark_mode))"
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
      ONLY="${1:-}" _llm_deploy && spark_mark llm
      ;;
    recreate)
      # Apply .env changes (for example a new pin) without pulling images again.
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

  deploy [SERVICE]       Copy the stack, deploy and wait for health checks
  recreate [SERVICE]     Recreate containers after editing the runtime .env
  mode models|flash|comfyui
                         Switch the serving mode (rolls back when unhealthy)
  status                 Show Compose services
  logs [ARGS...]         Show Compose logs (for example: logs -f llm)
  health                 Check containers and model endpoints
  config                 Render the Compose configuration
  public-api             Publish the key-protected API through Tailscale Funnel
  start|stop|restart SERVICE

The runtime directory is ${DOT_SPARK_DIR:-~/.config/dgx-spark}.
EOF
      ;;
    *) dot_echo "  ✗ Unknown llm command: $action (see dot llm help)" 1 >&2; return 2 ;;
  esac
}
