---
name: shell-scripting
description: POSIX-compliant shell scripting best practices. Use when writing bash scripts, shell scripts, automation scripts, 셸 스크립트 작성, 배시 스크립트, 자동화 스크립트.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Shell Scripting Best Practices

## Script Header

```bash
#!/bin/bash
set -euo pipefail

# Description: Brief description of what this script does
# Usage: ./script.sh [options] <args>
```

### Set Options
- `set -e`: Exit on error
- `set -u`: Error on undefined variables
- `set -o pipefail`: Fail on pipe errors
- `set -x`: Debug mode (print commands)

## Variables

### Declaration
```bash
# Use lowercase for local variables
local_var="value"

# Use uppercase for exported/environment variables
export PATH_PREFIX="/usr/local"

# Use readonly for constants
readonly CONFIG_FILE="/etc/app/config"
```

### Quoting
```bash
# Always quote variables
echo "$variable"
file_path="$HOME/documents/$filename"

# Use curly braces for clarity
echo "${var}_suffix"
echo "${array[0]}"
```

### Default Values
```bash
# Default if unset
name="${1:-default_value}"

# Error if unset
name="${1:?Error: name required}"

# Assign default if unset
: "${VAR:=default}"
```

## Conditionals

### File Tests
```bash
[[ -f "$file" ]]    # File exists
[[ -d "$dir" ]]     # Directory exists
[[ -r "$file" ]]    # Readable
[[ -w "$file" ]]    # Writable
[[ -x "$file" ]]    # Executable
[[ -s "$file" ]]    # Non-empty
```

### String Tests
```bash
[[ -z "$str" ]]     # Empty string
[[ -n "$str" ]]     # Non-empty string
[[ "$a" == "$b" ]]  # Equal
[[ "$a" != "$b" ]]  # Not equal
[[ "$a" =~ regex ]] # Regex match
```

### Numeric Comparison
```bash
[[ "$a" -eq "$b" ]] # Equal
[[ "$a" -ne "$b" ]] # Not equal
[[ "$a" -lt "$b" ]] # Less than
[[ "$a" -gt "$b" ]] # Greater than
(( a > b ))         # Arithmetic comparison
```

### Best Practices
```bash
# Use [[ ]] over [ ]
if [[ -f "$file" ]]; then
    echo "exists"
fi

# Combine conditions
if [[ -f "$file" && -r "$file" ]]; then
    cat "$file"
fi
```

## Functions

### Declaration
```bash
function_name() {
    local arg1="$1"
    local arg2="${2:-default}"

    # Function body

    return 0
}
```

### Best Practices
```bash
# Use local variables
my_function() {
    local result=""
    local -r readonly_var="constant"

    result="computed value"
    echo "$result"
}

# Capture output
output=$(my_function)

# Check return status
if my_function; then
    echo "success"
fi
```

## Error Handling

### Basic Pattern
```bash
# Exit with message
die() {
    echo "Error: $*" >&2
    exit 1
}

# Usage
[[ -f "$config" ]] || die "Config file not found"
```

### Cleanup on Exit
```bash
cleanup() {
    rm -f "$temp_file"
    echo "Cleaned up"
}
trap cleanup EXIT
```

### Error Context
```bash
set -euo pipefail

# Show line number on error
trap 'echo "Error on line $LINENO"' ERR
```

## Input/Output

### Reading Input
```bash
# Read line
read -r line

# Read with prompt
read -rp "Enter name: " name

# Read password (no echo)
read -rsp "Password: " password

# Read file line by line
while IFS= read -r line; do
    echo "$line"
done < "$file"
```

### Output
```bash
# Standard output
echo "message"
printf "Formatted: %s\n" "$value"

# Standard error
echo "error message" >&2

# Redirect both
command > output.log 2>&1
command &> output.log  # Bash shorthand
```

## Loops

### For Loop
```bash
# Over list
for item in a b c; do
    echo "$item"
done

# Over array
for item in "${array[@]}"; do
    echo "$item"
done

# Over files (use glob, not ls)
for file in *.txt; do
    [[ -f "$file" ]] || continue
    echo "$file"
done

# C-style
for ((i=0; i<10; i++)); do
    echo "$i"
done
```

### While Loop
```bash
while [[ "$count" -lt 10 ]]; do
    ((count++))
done

# Read lines
while IFS= read -r line; do
    process "$line"
done < "$file"
```

## Arrays

```bash
# Declaration
array=(one two three)
declare -a array

# Access
echo "${array[0]}"
echo "${array[@]}"     # All elements
echo "${#array[@]}"    # Length

# Append
array+=("four")

# Iterate
for item in "${array[@]}"; do
    echo "$item"
done
```

## Common Patterns

### Argument Parsing
```bash
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--file)
            FILE="$2"
            shift 2
            ;;
        *)
            die "Unknown option: $1"
            ;;
    esac
done
```

### Temp Files
```bash
temp_file=$(mktemp)
trap 'rm -f "$temp_file"' EXIT
```

### Check Dependencies
```bash
require_command() {
    command -v "$1" >/dev/null 2>&1 || die "$1 is required"
}

require_command jq
require_command curl
```

## Anti-Patterns to Avoid

```bash
# Bad: Parsing ls output
for f in $(ls *.txt); do  # WRONG

# Good: Use glob
for f in *.txt; do

# Bad: Unquoted variables
echo $variable  # WRONG

# Good: Quote variables
echo "$variable"

# Bad: Using eval
eval "$user_input"  # DANGEROUS

# Bad: Cat into while
cat file | while read line; do  # Subshell issues

# Good: Redirect into while
while read -r line; do
    ...
done < file
```
