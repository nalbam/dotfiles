#!/bin/bash

# cursor.sh - Cursor 앱을 실행하는 스크립트
# 사용법: cursor.sh [path]

# 기본 경로 설정 (파라미터가 없을 경우 현재 디렉토리 사용)
PATH_TO_OPEN="${1:-.}"

# Cursor 앱 실행
open -a "Cursor" "$PATH_TO_OPEN"

exit 0
