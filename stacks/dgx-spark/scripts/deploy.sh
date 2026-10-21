#!/usr/bin/env bash

set -euo pipefail
# Runs on DGX OS (Bash 5); empty arrays under set -u need Bash 4.4 or newer.
(( BASH_VERSINFO[0] * 100 + BASH_VERSINFO[1] >= 404 )) || { echo "${0##*/} needs Bash 4.4 or newer." >&2; exit 1; }

cd "$(dirname "$0")/.."

for command_name in docker nvidia-smi tailscale python3; do
  command -v "$command_name" >/dev/null || { echo "$command_name is required." >&2; exit 1; }
done
[[ "$(uname -m)" == aarch64 ]] || { echo "DGX Spark deployment requires aarch64." >&2; exit 1; }
nvidia-smi >/dev/null || { echo "NVIDIA GPU is not available." >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker is not available to $USER." >&2; exit 1; }
docker compose version >/dev/null || { echo "Docker Compose plugin is required." >&2; exit 1; }

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

tailscale wait --timeout=120s
TAILSCALE_IP="$(tailscale ip -4)"
SPARK_MODE="${SPARK_MODE:-models}"
COMFYUI_IMAGE="${COMFYUI_IMAGE:-dockpad-comfyui:v0.34.5}"
COMFYUI_VERSION="${COMFYUI_VERSION:-v0.34.5}"
NGC_PYTORCH_IMAGE="${NGC_PYTORCH_IMAGE:-nvcr.io/nvidia/pytorch:25.11-py3}"
COMFYUI_DATA_PATH="${COMFYUI_DATA_PATH:-$HOME/.local/share/comfyui}"
VLLM_IMAGE="${VLLM_IMAGE:-vllm/vllm-openai:v0.30.0}"
LLM_MODEL="${LLM_MODEL:-nvidia/Qwen3.6-35B-A3B-NVFP4}"
LLM_MAX_MODEL_LEN="${LLM_MAX_MODEL_LEN:-262144}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-Qwen/Qwen3-Embedding-4B}"
RERANKER_MODEL="${RERANKER_MODEL:-Qwen/Qwen3-Reranker-0.6B}"
FLASH_IMAGE="${FLASH_IMAGE:-dockpad-tensorfold-flash:v0.6.1-ko2}"
FLASH_MODEL="${FLASH_MODEL:-TensorFold/Qwen3.8-Flash-Next-MLX-4bit-MTP}"
FLASH_REVISION="${FLASH_REVISION:-2b170fa6309d5d1ee380b35636075fac7945f286}"
FLASH_MAX_MODEL_LEN="${FLASH_MAX_MODEL_LEN:-262144}"
FLASH_MAX_NUM_SEQS="${FLASH_MAX_NUM_SEQS:-4}"
FLASH_HOST_RESERVE_GIB="${FLASH_HOST_RESERVE_GIB:-8}"
FLASH_THINKING_BUDGET="${FLASH_THINKING_BUDGET:-512}"
FLASH_DRAFT_VOCAB="${FLASH_DRAFT_VOCAB:-multilingual}"

[[ "$TAILSCALE_IP" =~ ^100\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "invalid Tailscale IPv4: $TAILSCALE_IP" >&2; exit 1; }
[[ "$SPARK_MODE" == comfyui || "$SPARK_MODE" == models || "$SPARK_MODE" == flash ]] || { echo "SPARK_MODE must be comfyui, models or flash." >&2; exit 1; }
[[ "$LLM_MAX_MODEL_LEN" =~ ^[0-9]+$ ]] || { echo "LLM_MAX_MODEL_LEN must be an integer." >&2; exit 1; }
[[ "$COMFYUI_DATA_PATH" =~ ^/[a-zA-Z0-9._/-]+$ ]] || { echo "invalid COMFYUI_DATA_PATH: $COMFYUI_DATA_PATH" >&2; exit 1; }
[[ "$FLASH_MAX_MODEL_LEN" =~ ^[0-9]+$ ]] && (( 10#$FLASH_MAX_MODEL_LEN >= 1024 && 10#$FLASH_MAX_MODEL_LEN <= 262144 )) || { echo "FLASH_MAX_MODEL_LEN must be between 1024 and 262144." >&2; exit 1; }
[[ "$FLASH_REVISION" =~ ^[a-f0-9]{40}$ ]] || { echo "FLASH_REVISION must be a full commit SHA." >&2; exit 1; }
[[ "$FLASH_MAX_NUM_SEQS" =~ ^[0-9]+$ ]] && (( 10#$FLASH_MAX_NUM_SEQS >= 1 && 10#$FLASH_MAX_NUM_SEQS <= 4 )) || { echo "FLASH_MAX_NUM_SEQS must be between 1 and 4." >&2; exit 1; }
[[ "$FLASH_HOST_RESERVE_GIB" =~ ^[0-9]+$ ]] && (( 10#$FLASH_HOST_RESERVE_GIB >= 8 && 10#$FLASH_HOST_RESERVE_GIB <= 32 )) || { echo "FLASH_HOST_RESERVE_GIB must be between 8 and 32." >&2; exit 1; }
[[ "$FLASH_THINKING_BUDGET" =~ ^[0-9]+$ ]] && (( 10#$FLASH_THINKING_BUDGET >= 1 && 10#$FLASH_THINKING_BUDGET <= 8192 )) || { echo "FLASH_THINKING_BUDGET must be between 1 and 8192." >&2; exit 1; }
[[ "$FLASH_DRAFT_VOCAB" == multilingual || "$FLASH_DRAFT_VOCAB" == english_code ]] || { echo "FLASH_DRAFT_VOCAB must be multilingual or english_code." >&2; exit 1; }
for value in "$COMFYUI_IMAGE" "$COMFYUI_VERSION" "$NGC_PYTORCH_IMAGE" "$VLLM_IMAGE" "$LLM_MODEL" "$EMBEDDING_MODEL" "$RERANKER_MODEL" "$FLASH_IMAGE" "$FLASH_MODEL"; do
  [[ "$value" != *$'\n'* && "$value" != *' '* ]] || { echo "model settings must not contain whitespace." >&2; exit 1; }
done

temporary="$(mktemp .env.XXXXXX)"
cleanup() {
  rm -f -- "$temporary"
}
trap cleanup EXIT
chmod 0600 "$temporary"
printf '%s\n' \
  "TAILSCALE_IP=$TAILSCALE_IP" \
  "SPARK_MODE=$SPARK_MODE" \
  "COMFYUI_IMAGE=$COMFYUI_IMAGE" \
  "COMFYUI_VERSION=$COMFYUI_VERSION" \
  "NGC_PYTORCH_IMAGE=$NGC_PYTORCH_IMAGE" \
  "COMFYUI_DATA_PATH=$COMFYUI_DATA_PATH" \
  "VLLM_IMAGE=$VLLM_IMAGE" \
  "LLM_MODEL=$LLM_MODEL" \
  "LLM_MAX_MODEL_LEN=$LLM_MAX_MODEL_LEN" \
  "EMBEDDING_MODEL=$EMBEDDING_MODEL" \
  "RERANKER_MODEL=$RERANKER_MODEL" \
  "FLASH_IMAGE=$FLASH_IMAGE" \
  "FLASH_MODEL=$FLASH_MODEL" \
  "FLASH_REVISION=$FLASH_REVISION" \
  "FLASH_MAX_MODEL_LEN=$FLASH_MAX_MODEL_LEN" \
  "FLASH_MAX_NUM_SEQS=$FLASH_MAX_NUM_SEQS" \
  "FLASH_HOST_RESERVE_GIB=$FLASH_HOST_RESERVE_GIB" \
  "FLASH_THINKING_BUDGET=$FLASH_THINKING_BUDGET" \
  "FLASH_DRAFT_VOCAB=$FLASH_DRAFT_VOCAB" > "$temporary"
if [[ -f .env ]]; then
  python3 -B - "$temporary" <<'PY'
import sys
from pathlib import Path

temporary = Path(sys.argv[1])
updates = dict(line.split("=", 1) for line in temporary.read_text().splitlines())
lines = []
for line in Path(".env").read_text().splitlines():
    key = line.partition("=")[0]
    lines.append(f"{key}={updates.pop(key)}" if key in updates else line)
lines.extend(f"{key}={value}" for key, value in updates.items())
temporary.write_text("\n".join(lines) + "\n")
PY
fi
if [[ "$SPARK_MODE" == flash ]]; then
  command -v systemctl >/dev/null || { echo "Flash requires systemd user services for its memory watchdog." >&2; exit 1; }
  systemctl --user show-environment >/dev/null
fi
if [[ ! -f .env ]] || ! cmp -s "$temporary" .env; then
  mv "$temporary" .env
  temporary=""
  echo "== updated .env for $TAILSCALE_IP"
fi

compose=(docker compose)
compose+=(--profile "$SPARK_MODE")
if [[ -s .env.grafana ]]; then
  # config.alloy reads account values from .env.grafana; a missing key breaks Alloy only after restart.
  missing_grafana_keys=()
  for key in GCLOUD_FM_URL GCLOUD_FM_USERNAME GCLOUD_PROM_URL GCLOUD_PROM_USERNAME GCLOUD_FM_COLLECTOR_ID GCLOUD_RW_API_KEY; do
    grep -Eq "^${key}=(\"[^\"]|[^\"])" .env.grafana || missing_grafana_keys+=("$key")
  done
  if (( ${#missing_grafana_keys[@]} > 0 )); then
    echo ".env.grafana is missing: ${missing_grafana_keys[*]}. Run dot add monitoring (or scripts/setup-grafana.sh) to add them." >&2
    exit 1
  fi
  compose+=(--profile monitoring)
fi
"${compose[@]}" config --quiet
python3 -B scripts/services.py list models >/dev/null

services=()
if [[ -n "${ONLY:-}" ]]; then
  services+=("$ONLY")
fi

if (( ${#services[@]} > 0 )); then
  active_services="$("${compose[@]}" config --services)"
  for service in "${services[@]}"; do
    if ! grep -Fxq -- "$service" <<< "$active_services"; then
      echo "Service is not enabled in $SPARK_MODE mode: $service; use scripts/switch-mode.sh first." >&2
      exit 1
    fi
  done
fi

if [[ "${DRY_RUN:-false}" == true ]]; then
  echo "DGX Spark configuration is valid."
  exit 0
fi

if [[ "${SKIP_PULL:-false}" != true ]]; then
  "${compose[@]}" pull --ignore-buildable "${services[@]}"
fi

build_comfyui=false
if (( ${#services[@]} == 0 )); then
  [[ "$SPARK_MODE" == comfyui ]] && build_comfyui=true
else
  for service in "${services[@]}"; do
    [[ "$service" == comfyui ]] && build_comfyui=true
  done
fi
if [[ "$build_comfyui" == true ]]; then
  build_args=(build)
  [[ "${SKIP_PULL:-false}" == true ]] || build_args+=(--pull)
  if [[ "${SKIP_BUILD:-false}" != true ]]; then
    "${compose[@]}" "${build_args[@]}" comfyui
  fi
  mkdir -p \
    "$COMFYUI_DATA_PATH/models" \
    "$COMFYUI_DATA_PATH/input" \
    "$COMFYUI_DATA_PATH/output" \
    "$COMFYUI_DATA_PATH/user" \
    "$COMFYUI_DATA_PATH/custom_nodes"
fi
if [[ "$SPARK_MODE" == flash && "${SKIP_BUILD:-false}" != true ]]; then
  build_args=(build)
  [[ "${SKIP_PULL:-false}" == true ]] || build_args+=(--pull)
  "${compose[@]}" "${build_args[@]}" flash
fi

if [[ "${SKIP_PULL:-false}" != true && ( "$SPARK_MODE" == models || "$SPARK_MODE" == flash ) ]]; then
  echo "== model snapshots"
  snapshot_args=(--mode "$SPARK_MODE")
  [[ -z "${ONLY:-}" ]] || snapshot_args+=("$ONLY")
  snapshots="$(python3 -B scripts/services.py snapshots "${snapshot_args[@]}")"
  while IFS=$'\t' read -r service model revision; do
    [[ -n "$service" ]] || continue
    snapshot_model_args=("$model")
    [[ -z "$revision" ]] || snapshot_model_args+=("$revision")
    "${compose[@]}" run --rm --no-deps -T \
      --entrypoint python3 -e HF_HUB_OFFLINE=0 -e TRANSFORMERS_OFFLINE=0 \
      "$service" \
      -c 'from huggingface_hub import snapshot_download; import sys; snapshot_download(repo_id=sys.argv[1], revision=sys.argv[2] if len(sys.argv) > 2 else None)' \
      "${snapshot_model_args[@]}" </dev/null >/dev/null
    echo "   $service: $model"
  done <<< "$snapshots"
fi
if [[ "$SPARK_MODE" == flash && "${SKIP_PULL:-false}" != true ]]; then
  "${compose[@]}" run --rm --no-deps -T --entrypoint python3 flash \
    /opt/dockpad/serve-flash.py --prepare-only </dev/null
fi

[[ "${PREPARE_ONLY:-false}" != true ]] || exit 0
python3 -B scripts/services.py write-targets "$SPARK_MODE"
for inactive_mode in models comfyui flash; do
  [[ "$inactive_mode" == "$SPARK_MODE" ]] || scripts/compose.sh stop-mode "$inactive_mode"
done

up_args=(up -d)
if [[ "${FORCE_RECREATE:-false}" == true ]]; then
  up_args+=(--force-recreate)
fi
"${compose[@]}" "${up_args[@]}" "${services[@]}"
if [[ "$SPARK_MODE" == flash ]]; then
  scripts/setup-flash-watch.sh
fi
