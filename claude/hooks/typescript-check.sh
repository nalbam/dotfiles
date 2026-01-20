#!/bin/sh

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""')

if [ -n "$file_path" ] && [ -f "$file_path" ]; then
  dir=$(dirname "$file_path")
  project_root="$dir"
  while [ "$project_root" != "/" ] && [ ! -f "$project_root/package.json" ]; do
    project_root=$(dirname "$project_root")
  done

  if [ -f "$project_root/tsconfig.json" ]; then
    cd "$project_root" && npx tsc --noEmit --pretty false 2>&1 | grep "$file_path" | head -10 >&2 || true
  fi
fi

echo "$input"
