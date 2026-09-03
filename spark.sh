#!/usr/bin/env bash

set -euo pipefail

SSH_TARGET="${SPARK_SSH_TARGET:-nalbam@spark-0702}"
SSH_KEY="${SPARK_SSH_KEY:-$HOME/.ssh/id_ed25519_bruce}"
VLLM_IMAGE="${SPARK_VLLM_IMAGE:-vllm/vllm-openai:v0.28.0}"
MODEL_HANDLE="${SPARK_MODEL_HANDLE:-nvidia/Qwen3.6-35B-A3B-NVFP4}"
MAX_MODEL_LEN="${SPARK_MAX_MODEL_LEN:-262144}"
CONTAINER_NAME="vllm-server"
TOTAL_STEPS=7
CURRENT_STEP=0
FORCE_COLOR=false
CONTROL_DIR=""
CONTROL_PATH=""

if [ "${1:-}" = "--remote" ]; then
  CURRENT_STEP=1
  if [ "${2:-}" = "--color" ]; then
    FORCE_COLOR=true
  fi
fi

if { [ -t 1 ] || [ "$FORCE_COLOR" = true ]; } && [ -z "${NO_COLOR:-}" ]; then
  RED=$'\033[31m'
  GREEN=$'\033[32m'
  YELLOW=$'\033[33m'
  BLUE=$'\033[34m'
  MAGENTA=$'\033[35m'
  CYAN=$'\033[36m'
  RESET=$'\033[0m'
else
  RED=""
  GREEN=""
  YELLOW=""
  BLUE=""
  MAGENTA=""
  CYAN=""
  RESET=""
fi

_banner() {
  printf '%b\n' "${CYAN}╔════════════════════════════════════════════════════════════════╗${RESET}"
  printf '%b\n' "${CYAN}║                     DGX SPARK vLLM SETUP                       ║${RESET}"
  printf '%b\n' "${CYAN}╚════════════════════════════════════════════════════════════════╝${RESET}"
}

_progress() {
  CURRENT_STEP=$((CURRENT_STEP + 1))
  printf '\n%b▶ [%s/%s] %s%b\n' "$CYAN" "$CURRENT_STEP" "$TOTAL_STEPS" "$*" "$RESET"
}

_info() {
  printf '%b  ℹ %s%b\n' "$BLUE" "$*" "$RESET"
}

_run() {
  printf '%b  → %s%b\n' "$MAGENTA" "$*" "$RESET"
}

_ok() {
  printf '%b  ✓ %s%b\n' "$GREEN" "$*" "$RESET"
}

_warn() {
  printf '%b  ⚠ %s%b\n' "$YELLOW" "$*" "$RESET"
}

_error() {
  printf '\n%b✗ ERROR: %s%b\n\n' "$RED" "$*" "$RESET" >&2
  exit 1
}

_retry() {
  local description="$1"
  local attempt=1
  local wait_time=5
  shift

  while [ "$attempt" -le 3 ]; do
    if "$@"; then
      return 0
    fi
    if [ "$attempt" -eq 3 ]; then
      break
    fi
    _warn "$description 실패, ${wait_time}초 후 재시도합니다. (${attempt}/3)"
    sleep "$wait_time"
    attempt=$((attempt + 1))
    wait_time=$((wait_time * 2))
  done

  _error "$description 실패"
}

_require_command() {
  command -v "$1" >/dev/null 2>&1 || _error "필수 명령을 찾을 수 없습니다: $1"
}

_cleanup() {
  if [ -n "$CONTROL_PATH" ]; then
    ssh -S "$CONTROL_PATH" -O exit "$SSH_TARGET" >/dev/null 2>&1 || true
  fi
  if [ -n "$CONTROL_DIR" ]; then
    rmdir "$CONTROL_DIR" >/dev/null 2>&1 || true
  fi
}

_local_main() {
  local model_list
  local remote_command
  local script_path
  local -a ssh_options

  _banner
  _progress "DGX Spark SSH 연결"

  [ -f "$SSH_KEY" ] || _error "SSH 키를 찾을 수 없습니다: $SSH_KEY"
  chmod 600 "$SSH_KEY"

  CONTROL_DIR="$(mktemp -d /tmp/spark-vllm.XXXXXX)"
  CONTROL_PATH="$CONTROL_DIR/socket"
  script_path="${BASH_SOURCE[0]}"
  ssh_options=(
    -i "$SSH_KEY"
    -o ControlMaster=auto
    -o ControlPersist=60
    -o "ControlPath=$CONTROL_PATH"
  )

  trap _cleanup EXIT

  _run "ssh -i $SSH_KEY $SSH_TARGET"
  ssh "${ssh_options[@]}" "$SSH_TARGET" 'true'
  _ok "SSH 연결 확인 완료"

  printf -v remote_command \
    'SPARK_VLLM_IMAGE=%q SPARK_MODEL_HANDLE=%q SPARK_MAX_MODEL_LEN=%q bash -s -- --remote --color' \
    "$VLLM_IMAGE" "$MODEL_HANDLE" "$MAX_MODEL_LEN"
  ssh "${ssh_options[@]}" "$SSH_TARGET" "$remote_command" < "$script_path"
  model_list="$(ssh "${ssh_options[@]}" "$SSH_TARGET" 'curl -fsS http://127.0.0.1:8000/v1/models')" \
    || _error "모델 목록을 가져오지 못했습니다."

  printf '\n%b╔════════════════════════════════════════════════════════════════╗%b\n' "$GREEN" "$RESET"
  printf '%b║                     vLLM SETUP COMPLETED                       ║%b\n' "$GREEN" "$RESET"
  printf '%b╚════════════════════════════════════════════════════════════════╝%b\n\n' "$GREEN" "$RESET"
  _info "사용 가능한 모델 목록"
  if command -v jq >/dev/null 2>&1; then
    printf '%s\n' "$model_list" | jq -r '.data[].id'
  else
    printf '%s\n' "$model_list"
  fi
  _info "로컬 터널: ssh -N -L 8000:127.0.0.1:8000 -i $SSH_KEY $SSH_TARGET"
  _info "OpenAI-compatible endpoint: http://127.0.0.1:8000/v1"
}

_remote_main() {
  local architecture
  local container_label
  local container_model
  local container_state
  local response
  local attempt

  _progress "DGX Spark 환경 확인"
  _require_command nvidia-smi
  _require_command docker
  _require_command curl

  architecture="$(uname -m)"
  [ "$architecture" = "aarch64" ] || _error "지원하지 않는 아키텍처입니다: $architecture (aarch64 필요)"
  nvidia-smi >/dev/null || _error "NVIDIA GPU를 확인할 수 없습니다."
  if ! docker info >/dev/null 2>&1; then
    _error "Docker 접근에 실패했습니다. 원격에서 'sudo usermod -aG docker \"$USER\"' 실행 후 다시 로그인하세요."
  fi
  _ok "aarch64, NVIDIA GPU, Docker 확인 완료"

  _progress "vLLM 이미지 다운로드"
  _info "이미지: $VLLM_IMAGE"
  _retry "vLLM 이미지 다운로드" docker pull "$VLLM_IMAGE"
  _ok "vLLM 이미지 준비 완료"

  _progress "컨테이너 GPU 접근 확인"
  docker run --rm --gpus all --entrypoint nvidia-smi "$VLLM_IMAGE" >/dev/null \
    || _error "컨테이너에서 GPU에 접근할 수 없습니다. NVIDIA Container Toolkit 설정을 확인하세요."
  _ok "컨테이너 GPU 접근 확인 완료"

  _progress "모델 캐시 준비"
  mkdir -p "$HOME/.cache/huggingface"
  _info "모델: $MODEL_HANDLE"
  _info "최대 context length: $MAX_MODEL_LEN"
  if [ -f "$HOME/.cache/huggingface/token" ]; then
    _ok "Hugging Face token 확인 완료"
  else
    _warn "Hugging Face token이 없습니다. 공개 모델로 계속 진행합니다."
  fi

  _progress "vLLM 서버 기동"
  if docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
    container_label="$(docker inspect --format '{{ index .Config.Labels "com.nalbam.spark-vllm" }}' "$CONTAINER_NAME")"
    [ "$container_label" = "true" ] \
      || _error "'$CONTAINER_NAME' 컨테이너가 이미 존재하며 이 스크립트가 생성한 컨테이너가 아닙니다."
    container_model="$(docker inspect --format '{{ index .Config.Labels "com.nalbam.spark-vllm.model" }}' "$CONTAINER_NAME")"
    [ "$container_model" = "$MODEL_HANDLE" ] \
      || _error "기존 컨테이너 모델은 '$container_model'입니다. 요청 모델 '$MODEL_HANDLE'과 다릅니다."

    container_state="$(docker inspect --format '{{.State.Running}}' "$CONTAINER_NAME")"
    if [ "$container_state" = "true" ]; then
      _info "실행 중인 $CONTAINER_NAME 컨테이너를 재사용합니다."
    else
      docker start "$CONTAINER_NAME" >/dev/null
      _ok "$CONTAINER_NAME 컨테이너를 다시 시작했습니다."
    fi
  else
    docker run -d \
      --name "$CONTAINER_NAME" \
      --restart unless-stopped \
      --label com.nalbam.spark-vllm=true \
      --label "com.nalbam.spark-vllm.model=$MODEL_HANDLE" \
      --gpus all \
      --ipc host \
      --ulimit memlock=-1 \
      --ulimit stack=67108864 \
      --entrypoint "" \
      -p 127.0.0.1:8000:8000 \
      -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
      "$VLLM_IMAGE" \
      vllm serve "$MODEL_HANDLE" \
        --trust-remote-code \
        --tensor-parallel-size 1 \
        --kv-cache-dtype fp8 \
        --attention-backend flashinfer \
        --moe-backend marlin \
        --max-model-len "$MAX_MODEL_LEN" \
        --gpu-memory-utilization 0.5 \
        --max-num-seqs 8 \
        --max-num-batched-tokens 8192 \
        --enable-chunked-prefill \
        --async-scheduling \
        --enable-prefix-caching \
        --load-format fastsafetensors \
        --enable-auto-tool-choice \
        --tool-call-parser qwen3_xml \
        --reasoning-parser qwen3 \
        --mm-encoder-tp-mode data \
        --speculative-config '{"method":"mtp","num_speculative_tokens":3,"moe_backend":"triton"}' >/dev/null
    _ok "$CONTAINER_NAME 컨테이너를 생성했습니다."
  fi

  _info "모델 로딩을 기다립니다. 최초 실행은 수십 분 걸릴 수 있습니다."
  attempt=1
  while [ "$attempt" -le 180 ]; do
    if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
      _ok "vLLM health check 통과"
      break
    fi
    if [ "$attempt" -eq 180 ]; then
      docker logs --tail 100 "$CONTAINER_NAME" >&2
      _error "30분 안에 vLLM 서버가 준비되지 않았습니다."
    fi
    sleep 10
    attempt=$((attempt + 1))
  done

  _progress "OpenAI-compatible API 검증"
  response="$(curl -fsS http://127.0.0.1:8000/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{
      "model": "'"$MODEL_HANDLE"'",
      "messages": [{"role": "user", "content": "한 문장으로 DGX Spark를 설명해줘."}],
      "max_tokens": 512
    }')" || _error "chat completions API 호출에 실패했습니다."

  printf '%s' "$response" | grep -q '"choices"' \
    || _error "API 응답에서 choices를 찾을 수 없습니다: $response"
  _ok "API 응답 검증 완료"
  _info "원격 endpoint: http://127.0.0.1:8000/v1"
}

if [ "${1:-}" = "--remote" ]; then
  _remote_main
else
  _local_main
fi
