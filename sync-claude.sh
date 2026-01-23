#!/bin/bash

################################################################################
# sync-claude.sh - Interactive Claude Code settings sync
#
# Syncs ~/.dotfiles/claude/ to ~/.claude/ with diff preview and user confirmation
#
# Usage:
#   ./sync-claude.sh          # Interactive mode (default)
#   ./sync-claude.sh -y       # Auto-yes mode (skip prompts)
#   ./sync-claude.sh -n       # Dry-run mode (show changes only)
################################################################################

# Directories
SOURCE_DIR="${HOME}/.dotfiles/claude"
TARGET_DIR="${HOME}/.claude"

# Options
AUTO_YES=false
DRY_RUN=false
SYNC_ALL=false

# Counters
COUNT_NEW=0
COUNT_UPDATED=0
COUNT_SKIPPED=0
COUNT_IDENTICAL=0

# Colors
command -v tput >/dev/null && TPUT=true

################################################################################
# Helper Functions
################################################################################

_echo() {
  if [ "${TPUT}" != "" ] && [ "$2" != "" ]; then
    echo -e "$(tput setaf $2)$1$(tput sgr0)"
  else
    echo -e "$1"
  fi
}

_info() {
  _echo "  ℹ $@" 4
}

_ok() {
  _echo "  ✓ $@" 2
}

_skip() {
  _echo "  ⊘ $@" 3
}

_warn() {
  _echo "  ⚠ $@" 3
}

_new() {
  _echo "  + $@" 6
}

_diff_header() {
  _echo "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" 4
  _echo "  File: $1" 4
  _echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" 4
}

# Show diff between two files
_show_diff() {
  local source_file="$1"
  local target_file="$2"

  if command -v colordiff >/dev/null 2>&1; then
    diff -u "$target_file" "$source_file" | colordiff | head -50
  else
    diff -u "$target_file" "$source_file" | head -50
  fi

  local total_lines=$(diff -u "$target_file" "$source_file" | wc -l)
  if [ "$total_lines" -gt 50 ]; then
    _warn "... (${total_lines} lines total, showing first 50)"
  fi
}

# Prompt user for action
# Returns: 0=yes, 1=no, 2=all, 3=quit
_prompt_sync() {
  local prompt="$1"

  if [ "$AUTO_YES" = true ] || [ "$SYNC_ALL" = true ]; then
    return 0
  fi

  if [ "$DRY_RUN" = true ]; then
    return 1
  fi

  while true; do
    _echo "\n  $prompt [y/n/a/q] " 5
    read -r -n 1 answer
    echo
    case "$answer" in
      y|Y) return 0 ;;
      n|N) return 1 ;;
      a|A) SYNC_ALL=true; return 0 ;;
      q|Q) return 3 ;;
      *) _warn "Please answer y(yes), n(no), a(all), or q(quit)" ;;
    esac
  done
}

# Get MD5 hash (cross-platform)
_md5() {
  if [ "$(uname)" == "Darwin" ]; then
    md5 -q "$1" 2>/dev/null
  else
    md5sum "$1" 2>/dev/null | awk '{print $1}'
  fi
}

# Check if file is binary
_is_binary() {
  local file="$1"
  if file "$file" | grep -q "text"; then
    return 1
  else
    return 0
  fi
}

# Copy file with directory creation
_copy_file() {
  local source_file="$1"
  local target_file="$2"

  local target_dir=$(dirname "$target_file")
  if [ ! -d "$target_dir" ]; then
    mkdir -p "$target_dir"
  fi

  cp "$source_file" "$target_file"
}

################################################################################
# Main Logic
################################################################################

# Parse arguments
while getopts "ynh" opt; do
  case $opt in
    y) AUTO_YES=true ;;
    n) DRY_RUN=true ;;
    h)
      echo "Usage: $0 [-y] [-n] [-h]"
      echo "  -y  Auto-yes mode (sync all without prompts)"
      echo "  -n  Dry-run mode (show changes only)"
      echo "  -h  Show this help"
      exit 0
      ;;
    *)
      echo "Usage: $0 [-y] [-n] [-h]"
      exit 1
      ;;
  esac
done

# Banner
_echo "\n╔════════════════════════════════════════════════════════════════╗" 6
_echo "║                   CLAUDE CODE SETTINGS SYNC                    ║" 6
_echo "╚════════════════════════════════════════════════════════════════╝" 6

if [ "$DRY_RUN" = true ]; then
  _warn "Dry-run mode: No files will be modified"
fi

if [ "$AUTO_YES" = true ]; then
  _info "Auto-yes mode: All changes will be applied"
fi

# Check source directory
if [ ! -d "$SOURCE_DIR" ]; then
  _warn "Source directory not found: $SOURCE_DIR"
  _warn "Please run dotfiles installer first or clone the repository"
  exit 1
fi

# Create target directory if needed
if [ ! -d "$TARGET_DIR" ]; then
  _info "Creating target directory: $TARGET_DIR"
  if [ "$DRY_RUN" = false ]; then
    mkdir -p "$TARGET_DIR"
  fi
fi

_echo "\n▶ Comparing files..." 6
_info "Source: $SOURCE_DIR"
_info "Target: $TARGET_DIR"

# Find all files in source directory
while IFS= read -r -d '' source_file; do
  # Get relative path
  rel_path="${source_file#$SOURCE_DIR/}"
  target_file="$TARGET_DIR/$rel_path"

  # Check if target exists
  if [ ! -f "$target_file" ]; then
    # New file
    _diff_header "$rel_path"
    _new "NEW FILE"

    if ! _is_binary "$source_file"; then
      _echo "  Content preview:" 4
      head -20 "$source_file" | sed 's/^/    /'
      total_lines=$(wc -l < "$source_file")
      if [ "$total_lines" -gt 20 ]; then
        _warn "    ... (${total_lines} lines total)"
      fi
    else
      _info "Binary file ($(du -h "$source_file" | cut -f1))"
    fi

    _prompt_sync "Add this new file?"
    case $? in
      0)
        if [ "$DRY_RUN" = false ]; then
          _copy_file "$source_file" "$target_file"
        fi
        _ok "Added: $rel_path"
        COUNT_NEW=$((COUNT_NEW + 1))
        ;;
      1)
        _skip "Skipped: $rel_path"
        COUNT_SKIPPED=$((COUNT_SKIPPED + 1))
        ;;
      3)
        _warn "Sync cancelled by user"
        break
        ;;
    esac

  else
    # File exists - compare
    source_md5=$(_md5 "$source_file")
    target_md5=$(_md5 "$target_file")

    if [ "$source_md5" = "$target_md5" ]; then
      # Identical
      COUNT_IDENTICAL=$((COUNT_IDENTICAL + 1))
    else
      # Different
      _diff_header "$rel_path"

      if ! _is_binary "$source_file"; then
        _show_diff "$source_file" "$target_file"
      else
        _info "Binary file changed"
        _info "  Source: $(du -h "$source_file" | cut -f1)"
        _info "  Target: $(du -h "$target_file" | cut -f1)"
      fi

      _prompt_sync "Apply this change?"
      case $? in
        0)
          if [ "$DRY_RUN" = false ]; then
            _copy_file "$source_file" "$target_file"
          fi
          _ok "Updated: $rel_path"
          COUNT_UPDATED=$((COUNT_UPDATED + 1))
          ;;
        1)
          _skip "Skipped: $rel_path"
          COUNT_SKIPPED=$((COUNT_SKIPPED + 1))
          ;;
        3)
          _warn "Sync cancelled by user"
          break
          ;;
      esac
    fi
  fi

done < <(find "$SOURCE_DIR" -type f -print0 | sort -z)

# Summary
_echo "\n╔════════════════════════════════════════════════════════════════╗" 2
_echo "║                         SYNC COMPLETE                          ║" 2
_echo "╚════════════════════════════════════════════════════════════════╝" 2
_echo ""
_info "Summary:"
_ok "  New files added:  $COUNT_NEW"
_ok "  Files updated:    $COUNT_UPDATED"
_skip "  Files skipped:    $COUNT_SKIPPED"
_info "  Already in sync:  $COUNT_IDENTICAL"
_echo ""
