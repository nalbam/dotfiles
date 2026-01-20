#!/bin/sh

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""')

if [ -n "$file_path" ]; then
  echo "[Hook] WARNING: Creating documentation file outside docs/" >&2
  echo "[Hook] File: $file_path" >&2
  echo "[Hook] Consider moving to docs/ directory" >&2
fi

echo "$input"
