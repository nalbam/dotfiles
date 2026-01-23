#!/bin/bash

# ESP32 상태 표시 Hook
# USB 시리얼 우선, HTTP fallback

DEBUG="${DEBUG:-0}"

debug_log() {
  if [[ "$DEBUG" == "1" ]]; then
    echo "[DEBUG] $*" >&2
  fi
}

# 입력 읽기 (타임아웃 5초)
read -t 5 input

# 이벤트 정보 추출
event_name=$(echo "$input" | jq -r '.hook_event_name' 2>/dev/null || echo "Unknown")
tool_name=$(echo "$input" | jq -r '.tool_name // empty' 2>/dev/null)
cwd=$(echo "$input" | jq -r '.cwd // empty' 2>/dev/null)

# 프로젝트 이름 추출
if [ -n "$cwd" ]; then
  project_name=$(basename "$cwd")
else
  project_name=""
fi

debug_log "Event: $event_name, Tool: $tool_name, Project: $project_name"

# 상태 결정
case "$event_name" in
  "SessionStart")
    state="session_start"
    ;;
  "PreToolUse")
    state="working"
    ;;
  "PostToolUse")
    state="tool_done"
    ;;
  "Stop")
    state="idle"
    ;;
  "Notification")
    state="notification"
    ;;
  *)
    state="unknown"
    ;;
esac

# JSON 페이로드 생성
payload=$(jq -n \
  --arg state "$state" \
  --arg event "$event_name" \
  --arg tool "$tool_name" \
  --arg project "$project_name" \
  '{state: $state, event: $event, tool: $tool, project: $project}')

debug_log "Payload: $payload"

# 전송 함수: USB 시리얼
send_serial() {
  local port="$1"
  local data="$2"

  if [ -c "$port" ]; then
    # 시리얼 포트 설정 (115200 baud)
    stty -f "$port" 115200 2>/dev/null || stty -F "$port" 115200 2>/dev/null
    echo "$data" > "$port" 2>/dev/null
    return $?
  fi
  return 1
}

# 전송 함수: HTTP
send_http() {
  local url="$1"
  local data="$2"

  curl -s -X POST "$url/status" \
    -H "Content-Type: application/json" \
    -d "$data" \
    --connect-timeout 2 \
    --max-time 5 \
    > /dev/null 2>&1
  return $?
}

# 전송 시도
sent=false

# 1. USB 시리얼 시도
if [ -n "${ESP32_SERIAL_PORT}" ]; then
  debug_log "Trying USB serial: ${ESP32_SERIAL_PORT}"
  if send_serial "${ESP32_SERIAL_PORT}" "$payload"; then
    debug_log "Sent via USB serial"
    sent=true
  else
    debug_log "USB serial failed"
  fi
fi

# 2. HTTP fallback
if [ "$sent" = false ] && [ -n "${ESP32_HTTP_URL}" ]; then
  debug_log "Trying HTTP: ${ESP32_HTTP_URL}"
  if send_http "${ESP32_HTTP_URL}" "$payload"; then
    debug_log "Sent via HTTP"
    sent=true
  else
    debug_log "HTTP failed"
  fi
fi

# 3. 자동 감지 (설정 없을 때)
if [ "$sent" = false ] && [ -z "${ESP32_SERIAL_PORT}" ] && [ -z "${ESP32_HTTP_URL}" ]; then
  # macOS USB 시리얼 자동 감지
  for port in /dev/cu.usbserial-* /dev/cu.usbmodem* /dev/cu.wchusbserial*; do
    if [ -c "$port" ]; then
      debug_log "Auto-detected serial port: $port"
      if send_serial "$port" "$payload"; then
        debug_log "Sent via auto-detected serial"
        sent=true
        break
      fi
    fi
  done
fi

if [ "$sent" = false ]; then
  debug_log "No ESP32 connection available"
fi

exit 0
