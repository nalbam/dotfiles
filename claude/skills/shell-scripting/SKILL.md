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
