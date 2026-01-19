---
name: shell-scripting
description: Shell scripting best practices. 셸 스크립트 작성, 배시 스크립트.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Shell Scripting

**Follow project's existing style.**

## Header
```bash
#!/bin/bash
set -euo pipefail

# With debugging option
#!/bin/bash
set -euo pipefail
[[ "${DEBUG:-}" == "true" ]] && set -x
```

## ShellCheck
```bash
# Install
brew install shellcheck  # macOS
apt install shellcheck   # Debian/Ubuntu

# Run
shellcheck script.sh
shellcheck -x script.sh  # Follow sourced files

# Disable specific rule
# shellcheck disable=SC2034
unused_var="this is intentional"
```

## Variables
```bash
# Quote variables
echo "$variable"
name="${1:-default}"
readonly CONFIG="/etc/app/config"
```

## Conditionals
```bash
[[ -f "$file" ]]    # File exists
[[ -d "$dir" ]]     # Directory exists
[[ -z "$str" ]]     # Empty string
[[ "$a" == "$b" ]]  # Equal

if [[ -f "$file" ]]; then
  cat "$file"
fi
```

## Functions
```bash
my_func() {
  local arg1="$1"
  echo "$arg1"
}
```

## Loops
```bash
for item in "${array[@]}"; do
  echo "$item"
done

while IFS= read -r line; do
  echo "$line"
done < "$file"
```

## Error Handling
```bash
die() {
  echo "Error: $*" >&2
  exit 1
}

trap 'rm -f "$temp_file"' EXIT
```

## Arguments
```bash
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) show_help; exit 0 ;;
    -f|--file) FILE="$2"; shift 2 ;;
    *) die "Unknown: $1" ;;
  esac
done
```

## Avoid
```bash
# Bad
for f in $(ls *.txt); do    # Don't parse ls
echo $var                    # Unquoted variable
eval "$input"                # Dangerous

# Good
for f in *.txt; do
echo "$var"
```

## Debugging
```bash
# Enable trace mode
set -x                      # Print each command
set +x                      # Disable trace

# Custom trace prefix
PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'

# Debug specific section
set -x
# ... code to debug ...
set +x

# Verbose error on failure
trap 'echo "Error at line $LINENO: $BASH_COMMAND"' ERR
```

## Logging
```bash
# Simple logging
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log_info()  { log "INFO:  $*"; }
log_warn()  { log "WARN:  $*" >&2; }
log_error() { log "ERROR: $*" >&2; }

# Usage
log_info "Starting process"
log_error "Something failed"
```

## Color Output
```bash
# Colors (if terminal supports)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# Usage
echo -e "${GREEN}Success${NC}"
echo -e "${RED}Error${NC}"

# Check if terminal supports color
if [[ -t 1 ]]; then
  # stdout is a terminal, colors OK
  echo -e "${GREEN}Colored output${NC}"
else
  echo "Plain output"
fi
```

## Portable Scripts
```bash
# Use env for portability
#!/usr/bin/env bash

# Check for required commands
command -v jq >/dev/null 2>&1 || { echo "jq required"; exit 1; }

# OS detection
case "$(uname -s)" in
  Darwin*) OS="macos" ;;
  Linux*)  OS="linux" ;;
  *)       OS="unknown" ;;
esac
```
