#!/bin/sh

input=$(cat)

if git rev-parse --git-dir > /dev/null 2>&1; then
  modified_files=$(git diff --name-only HEAD 2>/dev/null | grep -E '\.(ts|tsx|js|jsx)$' || true)

  if [ -n "$modified_files" ]; then
    IFS_OLD="$IFS"
    IFS='
'
    for file in $modified_files; do
      if [ -f "$file" ]; then
        if grep -q "console\.log" "$file" 2>/dev/null; then
          echo "[Hook] WARNING: console.log found in $file" >&2
        fi
      fi
    done
    IFS="$IFS_OLD"
  fi
fi

echo "$input"
