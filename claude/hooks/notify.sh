#!/bin/bash

# 입력 읽기
read -t 5 input

# 이벤트 정보 추출
event_name=$(echo "$input" | jq -r '.hook_event_name' 2>/dev/null || echo "Unknown")

# 메시지 구성
case "$event_name" in
  "Stop")
    title="Claude Code"
    message="작업 완료"
    slack_message=":white_check_mark: Claude Code 작업 완료"
    ;;
  "Notification")
    title="Claude Code"
    message="입력을 기다리고 있습니다"
    slack_message=":question: Claude Code가 입력을 기다리고 있습니다"
    ;;
  *)
    title="Claude Code"
    message="$event_name"
    slack_message=":bell: Claude Code: $event_name"
    ;;
esac

# macOS 시스템 알림 + 사운드
if [[ "$OSTYPE" == "darwin"* ]]; then
  osascript -e "display notification \"$message\" with title \"$title\"" 2>/dev/null
  # 사운드 재생 (nohup으로 백그라운드 실행)
  if [ -f ~/.claude/sounds/success.mp3 ]; then
    nohup afplay ~/.claude/sounds/success.mp3 >/dev/null 2>&1 &
  fi
fi

# WSL (Windows Subsystem for Linux) 비프음 알림
if grep -qi microsoft /proc/version 2>/dev/null; then
  if command -v powershell.exe &> /dev/null; then
    powershell.exe -Command "[console]::beep(800, 300)" 2>/dev/null &
  fi
fi

# ntfy.sh 알림 (NTFY_TOPIC이 설정된 경우만)
if [ -n "${NTFY_TOPIC}" ]; then
  curl -s -X POST "https://ntfy.sh/${NTFY_TOPIC}" \
    -H "Title: ${title}" \
    -H "Tags: robot" \
    -d "${message}" > /dev/null 2>&1
fi

# Slack 알림 (SLACK_WEBHOOK_URL이 설정된 경우만)
if [ -n "${SLACK_WEBHOOK_URL}" ]; then
  curl -s -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"$slack_message\"}" \
    "${SLACK_WEBHOOK_URL}" > /dev/null 2>&1
fi

exit 0
