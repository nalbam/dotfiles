#!/bin/bash

# Debug mode (set DEBUG=1 to enable)
DEBUG="${DEBUG:-0}"

debug_log() {
  if [[ "$DEBUG" == "1" ]]; then
    echo "[DEBUG] $*" >&2
  fi
}

# 입력 읽기 (타임아웃 10초)
read -t 10 input

# 이벤트 정보 추출
event_name=$(echo "$input" | jq -r '.hook_event_name' 2>/dev/null || echo "Unknown")
cwd=$(echo "$input" | jq -r '.cwd // empty' 2>/dev/null)
transcript_path=$(echo "$input" | jq -r '.transcript_path // empty' 2>/dev/null)

# 프로젝트 이름 추출
if [ -n "$cwd" ]; then
  project_name=$(basename "$cwd")
elif [ -n "$transcript_path" ]; then
  # transcript_path: ~/.claude/projects/project-name/session.jsonl
  project_name=$(basename "$(dirname "$transcript_path")")
else
  project_name=""
fi

debug_log "Event: $event_name, Project: $project_name"

# 메시지 구성
case "$event_name" in
  "Stop")
    title="Claude Code"
    if [ -n "$project_name" ]; then
      message="[$project_name] 작업 완료"
      slack_message=":white_check_mark: Claude Code [$project_name] 작업 완료"
    else
      message="작업 완료"
      slack_message=":white_check_mark: Claude Code 작업 완료"
    fi
    ;;
  "Notification")
    title="Claude Code"
    if [ -n "$project_name" ]; then
      message="[$project_name] 입력을 기다리고 있습니다"
      slack_message=":question: Claude Code [$project_name] 입력을 기다리고 있습니다"
    else
      message="입력을 기다리고 있습니다"
      slack_message=":question: Claude Code가 입력을 기다리고 있습니다"
    fi
    ;;
  *)
    title="Claude Code"
    message="$event_name"
    slack_message=":bell: Claude Code: $event_name"
    ;;
esac

# macOS 시스템 알림 + 사운드
if [[ "$OSTYPE" == "darwin"* ]]; then
  debug_log "Sending macOS notification: $message"
  if osascript -e "display notification \"$message\" with title \"$title\"" 2>&1 | grep -v "^$" >&2; then
    debug_log "macOS notification sent successfully"
  fi

  # 사운드 재생 (nohup으로 백그라운드 실행)
  case "$event_name" in
    "Stop")
      sound_file=~/.claude/sounds/ding1.mp3
      ;;
    "Notification")
      sound_file=~/.claude/sounds/ding2.mp3
      ;;
    *)
      sound_file=~/.claude/sounds/ding3.mp3
      ;;
  esac

  if [ -f "$sound_file" ]; then
    debug_log "Playing sound: $sound_file"
    if [[ "$DEBUG" == "1" ]]; then
      afplay "$sound_file" 2>&1 | grep -v "^$" >&2
    else
      nohup afplay "$sound_file" >/dev/null 2>&1 &
    fi
  else
    debug_log "Sound file not found: $sound_file"
  fi
fi

# WSL (Windows Subsystem for Linux) 비프음 알림
if grep -qi microsoft /proc/version 2>/dev/null; then
  debug_log "WSL detected, sending beep notification"
  if command -v powershell.exe &> /dev/null; then
    if [[ "$DEBUG" == "1" ]]; then
      powershell.exe -Command "[console]::beep(800, 300)" 2>&1 | grep -v "^$" >&2
    else
      powershell.exe -Command "[console]::beep(800, 300)" 2>/dev/null &
    fi
    debug_log "WSL beep sent"
  else
    debug_log "powershell.exe not found"
  fi
fi

# ntfy.sh 알림 (NTFY_TOPIC이 설정된 경우만)
if [ -n "${NTFY_TOPIC}" ]; then
  debug_log "Sending ntfy.sh notification to topic: ${NTFY_TOPIC}"
  if [[ "$DEBUG" == "1" ]]; then
    curl -X POST "https://ntfy.sh/${NTFY_TOPIC}" \
      -H "Title: ${title}" \
      -H "Tags: robot" \
      -d "${message}" 2>&1 | head -3 >&2
  else
    curl -s -X POST "https://ntfy.sh/${NTFY_TOPIC}" \
      -H "Title: ${title}" \
      -H "Tags: robot" \
      -d "${message}" > /dev/null 2>&1
  fi
  debug_log "ntfy.sh notification sent"
fi

# Slack 알림 (SLACK_WEBHOOK_URL이 설정된 경우만)
if [ -n "${SLACK_WEBHOOK_URL}" ]; then
  debug_log "Sending Slack notification"
  if [[ "$DEBUG" == "1" ]]; then
    curl -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"$slack_message\"}" \
      "${SLACK_WEBHOOK_URL}" 2>&1 | head -3 >&2
  else
    curl -s -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"$slack_message\"}" \
      "${SLACK_WEBHOOK_URL}" > /dev/null 2>&1
  fi
  debug_log "Slack notification sent"
fi

exit 0
