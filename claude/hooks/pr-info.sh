#!/bin/sh

input=$(cat)
cmd=$(echo "$input" | jq -r '.tool_input.command')

if echo "$cmd" | grep -qE 'gh pr create'; then
  output=$(echo "$input" | jq -r '.tool_output.output // ""')
  pr_url=$(echo "$output" | grep -oE 'https://github.com/[^/]+/[^/]+/pull/[0-9]+')

  if [ -n "$pr_url" ]; then
    echo "[Hook] PR created: $pr_url" >&2
    repo=$(echo "$pr_url" | sed -E 's|https://github.com/([^/]+/[^/]+)/pull/[0-9]+|\1|')
    pr_num=$(echo "$pr_url" | sed -E 's|.*/pull/([0-9]+)|\1|')
    echo "[Hook] To review PR: gh pr review $pr_num --repo $repo" >&2
  fi
fi

echo "$input"
