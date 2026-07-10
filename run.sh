#!/bin/bash

# Wrap entire script in a block so the shell reads it fully into memory
# before execution. This prevents corruption when `git pull` updates this
# file while it is still running.
{

################################################################################
# 선언 영역 (Declaration Section)
################################################################################

# OS 정보 및 설치 도구 설정
OS_NAME="$(uname | awk '{print tolower($0)}' | cut -d'-' -f1)"
OS_ARCH="$(uname -m)"

if [ "${OS_NAME}" == "darwin" ]; then
  INSTALLER="brew"
elif [ "${OS_NAME}" == "linux" ]; then
  INSTALLER="apt"
elif [ "${OS_NAME}" == "mingw64_nt" ]; then
  INSTALLER="winget"
fi

# 설치 진행 단계 설정
TOTAL_STEPS=11
CURRENT_STEP=0

# 경고 카운터 (최종 요약에 사용)
WARN_COUNT=0

# 타이머 설정
UPDATE_INTERVAL=21600  # 6시간 (초 단위)

# 컬러 출력 설정
command -v tput >/dev/null && TPUT=true

################################################################################
# 함수 영역 (Function Section)
################################################################################

# 컬러 출력 함수
_echo() {
  if [ "${TPUT}" != "" ] && [ "$2" != "" ]; then
    echo -e "$(tput setaf $2)$1$(tput sgr0)"
  else
    echo -e "$1"
  fi
}

# 시작 배너 출력 함수
_banner() {
  _echo
  _echo "╔════════════════════════════════════════════════════════════════╗" 6
  _echo "║                       DOTFILES INSTALLER                       ║" 6
  _echo "║          Development Environment Setup Automation Tool         ║" 6
  _echo "╚════════════════════════════════════════════════════════════════╝" 6
}

# 진행률 표시 함수
_progress() {
  CURRENT_STEP=$((CURRENT_STEP + 1))
  _echo "\n▶ [$CURRENT_STEP/$TOTAL_STEPS] $@" 6
}

# 정보 메시지 출력 함수 (파랑)
_info() {
  _echo "  ℹ $@" 4
}

# 성공 메시지 출력 함수 (초록)
_ok() {
  _echo "  ✓ $@" 2
}

# 건너뛰기 메시지 출력 함수 (노랑)
_skip() {
  _echo "  ⊘ $@" 3
}

# 경고 메시지 출력 함수 (노랑)
# 주의: 서브셸($(...)·파이프)에서 호출하면 카운트가 유실됨 — 루프는 `< <(...)` 패턴 유지
_warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
  _echo "  ⚠ $@" 3
}

# 명령어 실행 표시 함수 (마젠타)
_run() {
  _echo "  → $@" 5
}

# 에러 메시지 출력 함수 (빨강)
_error() {
  _echo "\n✗ ERROR: $@\n" 1
  exit 1
}

# 최종 성공 메시지 출력 함수 (초록)
_success() {
  _echo
  _echo "╔════════════════════════════════════════════════════════════════╗" 2
  _echo "║                    INSTALLATION COMPLETED!                     ║" 2
  _echo "╚════════════════════════════════════════════════════════════════╝" 2
  if [ "${WARN_COUNT}" -gt 0 ]; then
    _echo "\n  ⚠ Completed with ${WARN_COUNT} warning(s) — review the ⚠ lines above." 3
  fi
  _echo
  exit 0
}

# 재시도 헬퍼 함수 (exponential backoff)
_retry() {
  local description="$1"
  shift
  local max_retries=3 retry_count=0 wait_time=5

  while [ $retry_count -lt $max_retries ]; do
    if "$@" 2>/dev/null; then return 0; fi
    retry_count=$((retry_count + 1))
    if [ $retry_count -eq $max_retries ]; then return 1; fi
    _info "$description failed, retrying in $wait_time seconds... (attempt $retry_count/$max_retries)"
    sleep $wait_time
    wait_time=$((wait_time * 2))
  done
}

# MD5 해시 함수 (크로스 플랫폼)
_md5() {
  if [ "${OS_NAME}" == "darwin" ]; then
    md5 -q "$1"
  else
    md5sum "$1" | awk '{print $1}'
  fi
}

_display_path() {
  case "$1" in
    "$HOME"/*) printf '~/%s' "${1#$HOME/}" ;;
    "$HOME") printf '~' ;;
    *) printf '%s' "$1" ;;
  esac
}

_show_changed_lines() {
  local old_file="$1"
  local new_file="$2"

  if ! command -v diff >/dev/null 2>&1; then
    return
  fi

  diff -u "$old_file" "$new_file" | awk '
    /^@@ / { print "    " $0; next }
    /^--- / || /^\+\+\+ / { next }
    /^-/ || /^\+/ { print "    " $0 }
  '
}

# 백업 생성 함수
_backup() {
  if [ -f "$1" ]; then
    if ! cp "$1" "$1.backup"; then
      _error "Failed to create backup of $1"
    fi
    # Set secure permissions for backup files
    chmod 600 "$1.backup"
    _info "Created backup: $1.backup"
  fi
}

# 파일 다운로드 함수
_download() {
  # 대상 파일의 디렉토리 자동 생성
  local target_file=~/$1
  local target_dir=$(dirname "$target_file")
  if [ "$target_dir" != "$HOME" ] && [ ! -d "$target_dir" ]; then
    mkdir -p "$target_dir"
  fi

  if [ -f ~/.dotfiles/${2:-$1} ]; then
    if [ -f ~/$1 ]; then
      if [ "$(_md5 ~/.dotfiles/${2:-$1})" != "$(_md5 ~/$1)" ]; then
        _backup ~/$1
        cp ~/.dotfiles/${2:-$1} ~/$1
      fi
    else
      cp ~/.dotfiles/${2:-$1} ~/$1
    fi
  else
    _backup ~/$1
    if ! _retry "Download ${2:-$1}" curl -fsSL --connect-timeout 10 -o ~/$1 https://raw.githubusercontent.com/nalbam/dotfiles/main/${2:-$1}; then
      _error "Failed to download ${2:-$1} after 3 attempts"
    fi
  fi

  # Set appropriate permissions for sensitive files
  case "$1" in
    .ssh/* | .aws/* | *.backup)
      chmod 600 ~/$1
      ;;
  esac
}

# Dotfiles 저장소 관리 함수
_dotfiles() {
  if ! command -v git >/dev/null 2>&1; then
    _skip "git not found — skipping repository sync"
    return
  fi

  # macOS: CLT 미설치 상태의 git 스텁은 실행만 해도 GUI 팝업을 띄우므로 실행 전 차단
  if [ "${OS_NAME}" == "darwin" ] && ! xcode-select -p >/dev/null 2>&1; then
    _skip "Xcode CLT not installed — skipping repository sync (complete CLT install, then re-run)"
    return
  fi

  if [ ! -d ~/.dotfiles ]; then
    _run "Cloning dotfiles repository..."
    if _retry "Clone" git clone https://github.com/nalbam/dotfiles.git ~/.dotfiles; then
      _ok "Dotfiles repository cloned"
    else
      _error "Failed to clone dotfiles repository after 3 attempts"
    fi
  else
    cd ~/.dotfiles || _error "Failed to change directory to ~/.dotfiles"
    _run "Updating dotfiles repository..."
    if _retry "Pull" git pull; then
      _ok "Dotfiles repository updated"
    else
      cd - >/dev/null || _error "Failed to return to previous directory"
      _error "Failed to update dotfiles repository after 3 attempts"
    fi
    cd - >/dev/null || _error "Failed to return to previous directory"
  fi
}

# 일회성 legacy 정리: manifest 도입(2026-06) 이전 sync 잔존물 제거
# NOTE: 모든 머신이 한 번 이상 실행된 뒤(2026-12 이후) 이 함수와 호출부를 삭제할 것
_cleanup_legacy_vibe() {
  # Codex는 ~/.codex/skills 를 읽지 않음 (~/.agents/skills 스캔) - 디렉토리 전체 제거
  if [ -d "${HOME}/.codex/skills" ]; then
    rm -rf "${HOME}/.codex/skills"
    _info "Removed legacy ~/.codex/skills (Codex reads ~/.agents/skills)"
  fi

  # 과거 repo가 배포했다가 삭제한 Claude 스킬 (git 이력에서 추출)
  local legacy_claude_skills=(
    aws-operations branch-cleanup context-init context-load deps-audit
    flag-cleanup git-workflow k8s-troubleshoot release-notes reroll-buddy
    security-review shell-scripting
  )
  local skill
  for skill in "${legacy_claude_skills[@]}"; do
    # repo에 다시 추가된 스킬은 보호 (이중 안전장치)
    if [ -d "${HOME}/.claude/skills/${skill}" ] && [ ! -d "${HOME}/.dotfiles/claude/skills/${skill}" ]; then
      rm -rf "${HOME}/.claude/skills/${skill}"
      _info "Removed legacy skill: ~/.claude/skills/${skill}"
    fi
  done
}

_sync_codex_config() {
  local src_file="$1"
  local dst_file="$2"
  local begin_marker="# BEGIN dotfiles managed codex config"
  local end_marker="# END dotfiles managed codex config"
  local tmp_file="${dst_file}.tmp.$$"
  local managed_file="${dst_file}.managed.$$"
  local unmanaged_file="${dst_file}.unmanaged.$$"
  local stripped_file="${dst_file}.stripped.$$"
  local old_file="${dst_file}.old.$$"
  CODEX_CONFIG_DIFF_OLD=""

  if ! awk -v begin="$begin_marker" -v end="$end_marker" '
    $0 == begin { in_block = 1 }
    in_block { print }
    $0 == end { found = 1; in_block = 0 }
    END { exit found ? 0 : 1 }
  ' "$src_file" > "$managed_file"; then
    rm -f "$managed_file" "$unmanaged_file" "$stripped_file"
    _warn "Codex config template is missing managed markers; preserving $dst_file to avoid wiping runtime settings"
    return 0
  fi

  if [ ! -f "$dst_file" ]; then
    cp "$src_file" "$dst_file"
    chmod 600 "$dst_file"
    rm -f "$managed_file" "$unmanaged_file" "$stripped_file"
    return 2
  fi

  local dst_mode
  dst_mode=$(stat -c "%a" "$dst_file" 2>/dev/null || stat -f "%Lp" "$dst_file" 2>/dev/null)

  if grep -Fxq "$begin_marker" "$dst_file" && grep -Fxq "$end_marker" "$dst_file"; then
    awk -v begin="$begin_marker" -v end="$end_marker" -v managed="$managed_file" '
      function print_managed(line) {
        while ((getline line < managed) > 0) print line
        close(managed)
      }
      $0 == begin { print_managed(); in_block = 1; next }
      in_block && $0 == end { in_block = 0; next }
      !in_block { print }
    ' "$dst_file" > "$tmp_file"
  else
    awk -v begin="$begin_marker" -v end="$end_marker" '
      $0 != begin && $0 != end { print }
    ' "$managed_file" > "$unmanaged_file"

    if ! awk -v unmanaged="$unmanaged_file" '
      BEGIN {
        while ((getline line < unmanaged) > 0) template[++template_len] = line
        close(unmanaged)
      }
      NR <= template_len && $0 != template[NR] { exit 1 }
      NR == template_len { exit 0 }
      END { exit NR >= template_len ? 0 : 1 }
    ' "$dst_file"; then
      rm -f "$tmp_file" "$managed_file" "$unmanaged_file" "$stripped_file"
      _info "Codex config has no managed block and does not match the previous dotfiles template; preserving $dst_file to avoid wiping runtime settings"
      return 0
    fi

    awk -v unmanaged="$unmanaged_file" '
      BEGIN {
        while ((getline line < unmanaged) > 0) template[++template_len] = line
        close(unmanaged)
        stripping = 1
      }
      stripping && NR <= template_len && $0 == template[NR] { next }
      stripping && NR <= template_len && $0 != template[NR] {
        for (i = 1; i < NR; i++) print template[i]
        stripping = 0
      }
      stripping && NR == template_len + 1 && $0 == "" { next }
      { stripping = 0; print }
      END {
        if (NR < template_len) {
          for (i = 1; i <= NR; i++) print template[i]
        }
      }
    ' "$dst_file" > "$stripped_file"
    cat "$managed_file" > "$tmp_file"
    printf '\n' >> "$tmp_file"
    cat "$stripped_file" >> "$tmp_file"
  fi

  rm -f "$managed_file" "$unmanaged_file" "$stripped_file"

  if [ -n "$dst_mode" ]; then
    chmod "$dst_mode" "$tmp_file"
  fi

  if [ "$(_md5 "$tmp_file")" = "$(_md5 "$dst_file")" ]; then
    rm -f "$tmp_file"
    return 0
  fi

  cp "$dst_file" "$old_file"
  CODEX_CONFIG_DIFF_OLD="$old_file"
  mv "$tmp_file" "$dst_file"
  return 1
}

_sync_codex_rules() {
  local src_file="$1"
  local dst_file="$2"
  local begin_marker="# BEGIN dotfiles managed codex rules"
  local end_marker="# END dotfiles managed codex rules"
  local tmp_file="${dst_file}.tmp.$$"
  local managed_file="${dst_file}.managed.$$"
  local old_file="${dst_file}.old.$$"
  CODEX_CONFIG_DIFF_OLD=""

  if ! awk -v begin="$begin_marker" -v end="$end_marker" '
    $0 == begin { in_block = 1 }
    in_block { print }
    $0 == end { found = 1; in_block = 0 }
    END { exit found ? 0 : 1 }
  ' "$src_file" > "$managed_file"; then
    rm -f "$managed_file"
    _warn "Codex rules template is missing managed markers; preserving $dst_file to avoid wiping runtime rules"
    return 0
  fi

  if [ ! -f "$dst_file" ]; then
    cp "$src_file" "$dst_file"
    chmod 600 "$dst_file"
    rm -f "$managed_file"
    return 2
  fi

  local dst_mode
  dst_mode=$(stat -c "%a" "$dst_file" 2>/dev/null || stat -f "%Lp" "$dst_file" 2>/dev/null)

  if grep -Fxq "$begin_marker" "$dst_file" && grep -Fxq "$end_marker" "$dst_file"; then
    awk -v begin="$begin_marker" -v end="$end_marker" -v managed="$managed_file" '
      function print_managed(line) {
        while ((getline line < managed) > 0) print line
        close(managed)
      }
      $0 == begin { print_managed(); in_block = 1; next }
      in_block && $0 == end { in_block = 0; next }
      !in_block { print }
    ' "$dst_file" > "$tmp_file"
  else
    cat "$managed_file" > "$tmp_file"
    printf '\n' >> "$tmp_file"
    cat "$dst_file" >> "$tmp_file"
  fi

  rm -f "$managed_file"

  if [ -n "$dst_mode" ]; then
    chmod "$dst_mode" "$tmp_file"
  fi

  if [ "$(_md5 "$tmp_file")" = "$(_md5 "$dst_file")" ]; then
    rm -f "$tmp_file"
    return 0
  fi

  cp "$dst_file" "$old_file"
  CODEX_CONFIG_DIFF_OLD="$old_file"
  mv "$tmp_file" "$dst_file"
  return 1
}

# Claude Code의 settings.json, Kiro의 agents/default.json 등은 앱이 훅 등록·설정 변경으로
# 로컬에서 계속 mutate하는 JSON이다. 통째로 덮어쓰면 로컬에서 생긴 키가 매 sync마다 유실되므로,
# dst에 없는 키만 src에서 채워 넣는다.
_sync_json_fill_missing() {
  local src_file="$1"
  local dst_file="$2"
  local tmp_file="${dst_file}.tmp.$$"
  local old_file="${dst_file}.old.$$"
  JSON_FILL_DIFF_OLD=""

  if [ ! -f "$dst_file" ]; then
    cp "$src_file" "$dst_file"
    return 2
  fi

  if ! command -v jq >/dev/null 2>&1; then
    _warn "jq not found — skipping $dst_file merge (leaving it untouched)"
    return 0
  fi

  local dst_mode
  dst_mode=$(stat -c "%a" "$dst_file" 2>/dev/null || stat -f "%Lp" "$dst_file" 2>/dev/null)

  if ! jq -n --slurpfile dst "$dst_file" --slurpfile src "$src_file" '
    def fill(a; b):
      if (a|type) == "object" and (b|type) == "object" then
        reduce (b | keys_unsorted[]) as $k (a;
          if (a | has($k)) then .[$k] = fill(a[$k]; b[$k])
          else .[$k] = b[$k] end)
      else a end;
    fill($dst[0]; $src[0])
  ' > "$tmp_file" 2>/dev/null; then
    rm -f "$tmp_file"
    _warn "Failed to merge $dst_file (invalid JSON?) — leaving it untouched"
    return 0
  fi

  if [ -n "$dst_mode" ]; then
    chmod "$dst_mode" "$tmp_file"
  fi

  if [ "$(jq -S -c . "$tmp_file" 2>/dev/null)" = "$(jq -S -c . "$dst_file" 2>/dev/null)" ]; then
    rm -f "$tmp_file"
    return 0
  fi

  cp "$dst_file" "$old_file"
  JSON_FILL_DIFF_OLD="$old_file"
  mv "$tmp_file" "$dst_file"
  return 1
}

# AI 도구 설정 동기화 함수 (Claude Code, Codex, Kiro)
_sync_vibe() {
  # ~/.dotfiles 부재 시 전체 skip (_cleanup_legacy_vibe 의 재추가-스킬 보호조건도 repo 존재를 전제)
  if [ ! -d ~/.dotfiles ]; then
    _skip "~/.dotfiles not found — skipping AI tools sync"
    return
  fi

  local sync_targets=(
    "claude:${HOME}/.claude"
    "codex:${HOME}/.codex"
    "codex/skills:${HOME}/.agents/skills"
    "kiro:${HOME}/.kiro"
  )

  local count_new=0
  local count_updated=0
  local count_identical=0
  local count_pruned=0

  # manifest 저장 위치 (--vibe 단독 실행은 Step 2를 건너뛰므로 직접 생성)
  mkdir -p ~/.toast

  _cleanup_legacy_vibe

  for target_config in "${sync_targets[@]}"; do
    local src_subdir="${target_config%%:*}"
    local dst_dir="${target_config#*:}"
    local src_path="${HOME}/.dotfiles/${src_subdir}"
    local manifest_file="${HOME}/.toast/vibe_manifest_${src_subdir//\//_}"
    local manifest_tmp="${manifest_file}.tmp"

    # Skip if source directory doesn't exist or is empty
    # (의도적으로 prune도 건너뜀 - 불완전한 checkout에서 대량 삭제 방지)
    if [ ! -d "$src_path" ] || [ -z "$(ls -A "$src_path" 2>/dev/null)" ]; then
      _skip "$src_subdir/ (empty or not found)"
      continue
    fi

    _info "Syncing $src_subdir/ -> $dst_dir/"

    # Create target directory if needed
    mkdir -p "$dst_dir"
    : > "$manifest_tmp"

    local find_args=("$src_path" -type f -not -path '*/__pycache__/*' -not -name '*.pyc')
    # codex/skills 는 ~/.agents/skills 타깃으로 별도 배포 (Codex는 ~/.codex/skills 를 읽지 않음)
    if [ "$src_subdir" = "codex" ]; then
      find_args+=(-not -path "$src_path/skills/*")
    fi

    # Find and process all files
    while IFS= read -r -d '' src_file; do
      local rel_path="${src_file#$src_path/}"
      local dst_file="$dst_dir/$rel_path"

      # 이번 sync가 관리하는 파일 목록 기록 (복사 여부와 무관)
      printf '%s\n' "$rel_path" >> "$manifest_tmp"

      # Create parent directory if needed
      mkdir -p "$(dirname "$dst_file")"

      # Codex mutates config.toml with runtime state such as project trust and UI
      # preferences. Sync only the dotfiles-managed block and preserve runtime
      # sections outside that block.
      if [ "$src_subdir" = "codex" ] && [ "$rel_path" = "config.toml" ]; then
        _sync_codex_config "$src_file" "$dst_file"
        case "$?" in
          0)
            count_identical=$((count_identical + 1))
            ;;
          1)
            _ok "UPDATE: $src_subdir/$rel_path -> $(_display_path "$dst_file") (managed block only)"
            if [ -n "$CODEX_CONFIG_DIFF_OLD" ] && [ -f "$CODEX_CONFIG_DIFF_OLD" ]; then
              _show_changed_lines "$CODEX_CONFIG_DIFF_OLD" "$dst_file"
              rm -f "$CODEX_CONFIG_DIFF_OLD"
            fi
            _info "Changed only # BEGIN/END dotfiles managed codex config; preserved runtime sections outside it"
            count_updated=$((count_updated + 1))
            ;;
          2)
            _ok "+ NEW: $src_subdir/$rel_path -> $(_display_path "$dst_file")"
            _info "Created managed Codex config template; future syncs update only the marked block"
            count_new=$((count_new + 1))
            ;;
        esac
        continue
      fi

      # Codex also mutates rules/default.rules when the user accepts command
      # prefixes. Sync only the dotfiles-managed block and preserve local rules.
      if [ "$src_subdir" = "codex" ] && [ "$rel_path" = "rules/default.rules" ]; then
        _sync_codex_rules "$src_file" "$dst_file"
        case "$?" in
          0)
            count_identical=$((count_identical + 1))
            ;;
          1)
            _ok "UPDATE: $src_subdir/$rel_path -> $(_display_path "$dst_file") (managed block only)"
            if [ -n "$CODEX_CONFIG_DIFF_OLD" ] && [ -f "$CODEX_CONFIG_DIFF_OLD" ]; then
              _show_changed_lines "$CODEX_CONFIG_DIFF_OLD" "$dst_file"
              rm -f "$CODEX_CONFIG_DIFF_OLD"
            fi
            _info "Changed only # BEGIN/END dotfiles managed codex rules; preserved local rules outside it"
            count_updated=$((count_updated + 1))
            ;;
          2)
            _ok "+ NEW: $src_subdir/$rel_path -> $(_display_path "$dst_file")"
            _info "Created managed Codex rules template; future syncs update only the marked block"
            count_new=$((count_new + 1))
            ;;
        esac
        continue
      fi

      # Claude Code settings.json, Kiro agents/default.json, Codex hooks.json은 앱이 로컬에서
      # 계속 mutate하는 설정 파일이므로 통째로 덮어쓰지 않고 dst에 없는 키만 채워 넣는다.
      local is_fill_missing_json=false
      if [ "$src_subdir" = "claude" ] && [ "$rel_path" = "settings.json" ]; then
        is_fill_missing_json=true
      elif [ "$src_subdir" = "kiro" ] && [ "$rel_path" = "agents/default.json" ]; then
        is_fill_missing_json=true
      elif [ "$src_subdir" = "codex" ] && [ "$rel_path" = "hooks.json" ]; then
        is_fill_missing_json=true
      fi

      if [ "$is_fill_missing_json" = true ]; then
        _sync_json_fill_missing "$src_file" "$dst_file"
        case "$?" in
          0)
            count_identical=$((count_identical + 1))
            ;;
          1)
            _ok "UPDATE: $src_subdir/$rel_path -> $(_display_path "$dst_file") (missing keys only)"
            if [ -n "$JSON_FILL_DIFF_OLD" ] && [ -f "$JSON_FILL_DIFF_OLD" ]; then
              _show_changed_lines "$JSON_FILL_DIFF_OLD" "$dst_file"
              rm -f "$JSON_FILL_DIFF_OLD"
            fi
            _info "Added missing keys only; preserved existing local settings"
            count_updated=$((count_updated + 1))
            ;;
          2)
            _ok "+ NEW: $src_subdir/$rel_path -> $(_display_path "$dst_file")"
            count_new=$((count_new + 1))
            ;;
        esac
        continue
      fi

      if [ ! -f "$dst_file" ]; then
        # New file
        cp "$src_file" "$dst_file"
        _ok "+ NEW: $src_subdir/$rel_path -> $(_display_path "$dst_file")"
        count_new=$((count_new + 1))
      else
        # Existing file - compare
        local src_md5=$(_md5 "$src_file")
        local dst_md5=$(_md5 "$dst_file")

        if [ "$src_md5" = "$dst_md5" ]; then
          count_identical=$((count_identical + 1))
        else
          _ok "UPDATE: $src_subdir/$rel_path -> $(_display_path "$dst_file")"
          _show_changed_lines "$dst_file" "$src_file"
          cp "$src_file" "$dst_file"
          count_updated=$((count_updated + 1))
        fi
      fi
    done < <(find "${find_args[@]}" -print0 | sort -z)

    # Prune: 이전 manifest에 있으나 현재 소스에 없는 파일 = repo에서 삭제된 파일
    # manifest에 없는 파일(사용자 설치 자산)은 절대 건드리지 않음
    if [ -f "$manifest_file" ]; then
      while IFS= read -r rel_path; do
        case "$rel_path" in ""|/*|*..*) continue ;; esac # manifest 손상 방어
        local stale_file="$dst_dir/$rel_path"
        if [ -f "$stale_file" ]; then
          rm -f "$stale_file"
          _info "- PRUNE: $src_subdir/$rel_path -> $(_display_path "$stale_file") (removed from repo)"
          count_pruned=$((count_pruned + 1))
          # 비게 된 부모 디렉토리만 정리 (rmdir은 빈 디렉토리만 제거하므로 안전)
          local parent_dir=$(dirname "$stale_file")
          while [ "$parent_dir" != "$dst_dir" ] && rmdir "$parent_dir" 2>/dev/null; do
            parent_dir=$(dirname "$parent_dir")
          done
        fi
      done < <(comm -23 <(sort -u "$manifest_file") <(sort -u "$manifest_tmp"))
    fi

    mv "$manifest_tmp" "$manifest_file"
  done

  _info "Sync summary: $count_new new, $count_updated updated, $count_identical identical, $count_pruned pruned"
}

# NPM 패키지 설치 함수 (버전 체크 포함)
# NPM_CMD is set once before calling this function (see Step 6)
_install_npm_package() {
  local package_name="$1"
  local package_spec="$2"
  local npm_cmd="${NPM_CMD:-npm}"

  # npm 실행 가능 여부 확인 (node 미설치 시 npm 호출이 exit 127 반환)
  if ! npm --version >/dev/null 2>&1; then
    _warn "npm is not functional (is node installed?), skipping $package_name"
    return 1
  fi

  # Check if package is installed
  if npm list -g "$package_spec" >/dev/null 2>&1; then
    local installed_version=$(npm list -g "$package_spec" --depth=0 2>/dev/null | grep "$package_name" | sed 's/.*@\([0-9.]*\).*/\1/')
    local latest_version=$(npm view "$package_spec" version 2>/dev/null)

    if [ -n "$installed_version" ] && [ -n "$latest_version" ]; then
      if [ "$installed_version" != "$latest_version" ]; then
        _run "Updating $package_name: $installed_version → $latest_version"
        if $npm_cmd update -g "$package_spec" >/dev/null 2>&1; then
          _ok "$package_name updated to $latest_version"
        else
          _warn "Failed to update $package_name"
        fi
      else
        _skip "$package_name already up to date ($installed_version)"
      fi
    else
      _run "Installing $package_name..."
      if $npm_cmd install -g "$package_spec" >/dev/null 2>&1; then
        _ok "$package_name installed"
      else
        _warn "Failed to install $package_name"
      fi
    fi
  else
    _run "Installing $package_name..."
    if $npm_cmd install -g "$package_spec" >/dev/null 2>&1; then
      _ok "$package_name installed"
    else
      _warn "Failed to install $package_name"
    fi
  fi
}

# pip install/upgrade를 4단계 fallback으로 시도
_pip_try_install() {
  local package_name="$1"
  shift
  local flags="$@"

  python3 -m pip install $flags "$package_name" 2>/dev/null >/dev/null ||
  python3 -m pip install --user $flags "$package_name" 2>/dev/null >/dev/null ||
  python3 -m pip install --break-system-packages --user $flags "$package_name" 2>/dev/null >/dev/null ||
  sudo python3 -m pip install $flags "$package_name" 2>/dev/null >/dev/null
}

# PIP 패키지 설치 함수 (버전 체크 포함)
_install_pip_package() {
  local package_name="$1"

  # Python3 체크
  if ! command -v python3 >/dev/null 2>&1; then
    _skip "Python3 not found, skipping $package_name"
    return 1
  fi

  # Check if package is installed
  if python3 -m pip show "$package_name" >/dev/null 2>&1; then
    local installed_version=$(python3 -m pip show "$package_name" 2>/dev/null | grep "Version:" | awk '{print $2}')
    local latest_version=$(python3 -m pip index versions "$package_name" 2>/dev/null | grep "LATEST:" | awk '{print $2}')

    if [ -n "$installed_version" ] && [ -n "$latest_version" ]; then
      if [ "$installed_version" != "$latest_version" ]; then
        _run "Updating $package_name: $installed_version → $latest_version"
        if _pip_try_install "$package_name" --upgrade; then
          _ok "$package_name updated to $latest_version"
        else
          _warn "Failed to update $package_name after trying all methods"
        fi
      else
        _skip "$package_name already up to date ($installed_version)"
      fi
    else
      _run "Installing $package_name..."
      if _pip_try_install "$package_name"; then
        _ok "$package_name installed"
      else
        _warn "Failed to install $package_name after trying all methods"
      fi
    fi
  else
    _run "Installing $package_name..."
    if _pip_try_install "$package_name"; then
      local new_version=$(python3 -m pip show "$package_name" 2>/dev/null | grep "Version:" | awk '{print $2}')
      if [ -n "$new_version" ]; then
        _ok "$package_name installed (v$new_version)"
      else
        _ok "$package_name installed"
      fi
    else
      _warn "Failed to install $package_name after trying all methods"
    fi
  fi
}

# 업데이트 타이머 체크 함수 (12시간 간격)
_should_update() {
  local timestamp_file="$1"
  if [ ! -f "$timestamp_file" ]; then return 0; fi
  local time_diff=$(( $(date +%s) - $(cat "$timestamp_file") ))
  [ $time_diff -ge $UPDATE_INTERVAL ]
}

################################################################################
# 실행 영역 (Execution Section)
################################################################################

# 시작 배너 출력
_banner

# Parse arguments
VIBE_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --vibe) VIBE_ONLY=true ;;
  esac
done

if [ "$VIBE_ONLY" = true ]; then
  _info "Running AI tools sync only..."
  if [ -d ~/.dotfiles ]; then
    _sync_vibe
    if [ "${WARN_COUNT}" -gt 0 ]; then
      _echo "\n  ⚠ Sync completed with ${WARN_COUNT} warning(s) — review the ⚠ lines above." 3
    fi
    _echo "\n  ✓ AI tools sync complete\n" 2
    exit 0
  else
    _error "Dotfiles not installed. Run full install first."
  fi
fi

# Step 1: 시스템 환경 확인
_progress "Checking system environment..."
_info "Operating System: ${OS_NAME}"
_info "Architecture: ${OS_ARCH}"
_info "Package Manager: ${INSTALLER}"

if [ "${INSTALLER}" == "" ]; then
  _error "Unsupported operating system."
fi

# Step 2: 디렉토리 생성 및 SSH 키 설정
_progress "Creating directories and setting up SSH keys..."

mkdir -p ~/.aws
mkdir -p ~/.ssh
mkdir -p ~/.toast
_ok "Directories created"

# Generate SSH keys
if [ ! -f ~/.ssh/id_rsa ]; then
  if ssh-keygen -q -f ~/.ssh/id_rsa -N ''; then
    _ok "Generated RSA SSH key (~/.ssh/id_rsa)"
  else
    _warn "Failed to generate RSA SSH key"
  fi
else
  _skip "RSA SSH key already exists"
fi

if [ ! -f ~/.ssh/id_ed25519 ]; then
  if ssh-keygen -q -t ed25519 -f ~/.ssh/id_ed25519 -N ''; then
    _ok "Generated ED25519 SSH key (~/.ssh/id_ed25519)"
  else
    _warn "Failed to generate ED25519 SSH key"
  fi
else
  _skip "ED25519 SSH key already exists"
fi

# Step 3: Dotfiles 저장소 클론
_progress "Cloning dotfiles repository..."
_dotfiles

# Step 4: 기본 설정 파일 다운로드
_progress "Setting up basic configuration files..."

# SSH 설정 파일 다운로드
if [ ! -f ~/.ssh/config ]; then
  _download .ssh/config ssh/config
  _ok "Downloaded SSH config template"
  _info "To use 1Password: op read op://keys/ssh-config/notesPlain > ~/.ssh/config && chmod 600 ~/.ssh/config"
else
  _skip "SSH config already exists"
fi

# AWS 설정 파일 다운로드
if [ ! -f ~/.aws/config ]; then
  _download .aws/config aws/config
  _ok "Downloaded AWS config template"
  _info "To use 1Password for AWS:"
  _info "  op read op://keys/aws-config/notesPlain > ~/.aws/config && chmod 600 ~/.aws/config"
  _info "  op read op://keys/aws-credentials/notesPlain > ~/.aws/credentials && chmod 600 ~/.aws/credentials"
else
  _skip "AWS config already exists"
fi

# Git 설정 파일 다운로드
_download .gitconfig gitconfig
_download .gitconfig-bruce gitconfig-bruce
_download .gitconfig-nalbam gitconfig-nalbam
_ok "Git configuration files downloaded"

# Step 5: OS별 패키지 관리자 설정
_progress "Setting up package managers..."

# Linux 설정 (APT 패키지 관리)
if [ "${OS_NAME}" == "linux" ]; then
  APT_TIMESTAMP_FILE=~/.toast/last_update_apt

  if _should_update "$APT_TIMESTAMP_FILE"; then
    _run "Updating APT packages..."
    # 성공 시에만 timestamp 갱신 (실패 시 다음 실행에서 재시도)
    if sudo apt update && sudo apt upgrade -y; then
      _ok "APT packages updated"
      date +%s > "$APT_TIMESTAMP_FILE"
    else
      _warn "APT update failed — will retry on next run"
    fi
  else
    _skip "APT update (last update was less than 6 hours ago)"
  fi

  # 기본 패키지 설치 (없는 경우에만)
  if ! command -v zsh >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
    _run "Installing essential packages (build-essential, git, zsh, jq, etc.)..."
    sudo apt install -y build-essential procps curl file git unzip jq zsh
    _ok "Essential packages installed"
  else
    _skip "Essential packages already installed"
  fi
fi

# Homebrew 설치
if ! command -v brew >/dev/null 2>&1; then
  _run "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
  # 사후 검증: 설치 실패를 성공으로 보고하지 않는다
  if command -v brew >/dev/null 2>&1; then
    _ok "Homebrew installed"
  else
    _warn "Homebrew install failed — continuing without brew"
  fi
else
  _skip "Homebrew already installed"
fi

# Step 6: 개발 도구 패키지 설치
_progress "Installing development packages..."

# Homebrew 패키지 업데이트 (brew가 설치된 경우에만)
if command -v brew >/dev/null 2>&1; then
  BREW_TIMESTAMP_FILE=~/.toast/last_update_brew
  BREWFILE_SRC=~/.dotfiles/$OS_NAME/Brewfile

  # Brewfile 변경 감지: ~/.Brewfile 은 "마지막으로 bundle 성공한 내용" 마커
  BREWFILE_CHANGED=false
  if [ -f "$BREWFILE_SRC" ]; then
    if [ ! -f ~/.Brewfile ] || [ "$(_md5 "$BREWFILE_SRC")" != "$(_md5 ~/.Brewfile)" ]; then
      BREWFILE_CHANGED=true
    fi
  fi

  BREW_DUE=false
  if _should_update "$BREW_TIMESTAMP_FILE"; then BREW_DUE=true; fi

  BREW_OK=true
  if [ "$BREW_DUE" = true ]; then
    _run "Updating Homebrew packages..."
    if brew update && brew upgrade; then
      _ok "Homebrew packages updated"
    else
      _warn "brew update/upgrade failed"
      BREW_OK=false
    fi
  else
    _skip "Homebrew update (last update was less than 6 hours ago)"
  fi

  # Brewfile 설치: 스로틀 만료 또는 Brewfile 변경 시 (변경은 스로틀과 무관하게 즉시 반영)
  if [ -f "$BREWFILE_SRC" ]; then
    if [ "$BREW_DUE" = true ] || [ "$BREWFILE_CHANGED" = true ]; then
      _run "Installing packages from Brewfile..."
      if brew bundle --file="$BREWFILE_SRC"; then
        brew cleanup
        _ok "Brewfile packages installed"
        # 성공 후에만 마커 동기화 → 실패 시 다음 실행에서 CHANGED 로 재시도
        _download .Brewfile $OS_NAME/Brewfile
      else
        brew cleanup
        _warn "brew bundle failed — some packages did not install"
        BREW_OK=false
      fi
    fi
  else
    _skip "Brewfile not found for $OS_NAME"
  fi

  # 모든 단계 성공 시에만 timestamp 갱신 (실패 시 다음 실행에서 재시도)
  if [ "$BREW_DUE" = true ] && [ "$BREW_OK" = true ]; then
    date +%s > "$BREW_TIMESTAMP_FILE"
  fi

  # macOS getopt 설정
  if [ "${OS_NAME}" == "darwin" ]; then
    GETOPT=$(getopt 2>&1 | head -1 | xargs)
    if [ "${GETOPT}" == "--" ]; then
      brew link --force gnu-getopt
    fi
  fi
else
  _skip "Homebrew not found"
fi

# NPM 패키지 설치 (버전 체크 포함)
if command -v npm >/dev/null; then
  NPM_TIMESTAMP_FILE=~/.toast/last_update_npm

  if _should_update "$NPM_TIMESTAMP_FILE"; then
    _info "Installing/updating NPM packages..."

    # npm prefix 의 쓰기 권한 확인
    # sudo npm 은 brew 환경에서 lib/node_modules 에 root 소유 파일을 남겨
    # 이후 brew node 의 post_install 과 npm install 을 영구 EACCES 로 망가뜨린다
    # (자가 강화 권한 오염 사이클). 권한이 깨졌으면 도망가지 말고 멈춘다.
    NPM_PREFIX=$(npm config get prefix 2>/dev/null || echo "/usr/local")
    NPM_CMD="npm"
    NPM_OK=true
    NPM_NODE_MODULES="$NPM_PREFIX/lib/node_modules"

    # 컨테이너 디렉토리 자체의 쓰기 권한
    if [ -d "$NPM_NODE_MODULES" ] && [ ! -w "$NPM_NODE_MODULES" ]; then
      _warn "$NPM_NODE_MODULES is not user-writable."
      NPM_OK=false
    fi

    # 컨테이너는 user 소유여도 그 안의 패키지가 root 소유인 케이스 (과거 sudo npm 의 후유증)
    if [ "$NPM_OK" = true ] && [ -d "$NPM_NODE_MODULES" ]; then
      while IFS= read -r pkg_dir; do
        if [ ! -w "$pkg_dir" ]; then
          _warn "$pkg_dir is not user-writable (root-owned from past sudo npm)."
          NPM_OK=false
          break
        fi
      done < <(find "$NPM_NODE_MODULES" -mindepth 1 -maxdepth 1 -type d 2>/dev/null)
    fi

    if [ "$NPM_OK" = false ]; then
      _info "Do NOT use sudo npm — it permanently corrupts brew's node install."
      _info "Fix with: sudo chown -R \$(whoami):staff $NPM_NODE_MODULES"
      _info "Skipping NPM package install/update."
    fi

    if [ "$NPM_OK" = true ]; then
      # npm 자체는 brew 의 node 패키지가 관리하므로 self-update 시도하지 않음
      _install_npm_package "corepack" "corepack"
      _install_npm_package "serverless" "serverless"
      _install_npm_package "ccusage" "ccusage"

      date +%s > "$NPM_TIMESTAMP_FILE"
    fi
  else
    _skip "NPM packages update (last update was less than 6 hours ago)"
  fi
else
  _skip "NPM not found"
fi

# Claude Code 업데이트
if command -v claude >/dev/null; then
  CLAUDE_TIMESTAMP_FILE=~/.toast/last_update_claude

  if _should_update "$CLAUDE_TIMESTAMP_FILE"; then
    _run "Updating Claude Code..."
    claude_update_output=$(claude update 2>&1) || true
    if echo "$claude_update_output" | grep -q "Successfully updated"; then
      _ok "Claude Code updated"
    else
      _skip "Claude Code already up to date"
    fi

    # Update timestamp
    date +%s > "$CLAUDE_TIMESTAMP_FILE"
  else
    _skip "Claude Code update (last update was less than 6 hours ago)"
  fi
else
  _skip "Claude Code not found"
fi

# PIP 패키지 설치 (버전 체크 포함)
if command -v python3 >/dev/null; then
  PIP_TIMESTAMP_FILE=~/.toast/last_update_pip

  if _should_update "$PIP_TIMESTAMP_FILE"; then
    _info "Installing/updating PIP packages..."

    # 먼저 기본 도구들을 업데이트 (setuptools, wheel 등)
    _run "Ensuring pip, setuptools, and wheel are up to date..."
    if python3 -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || \
       python3 -m pip install --user --upgrade pip setuptools wheel >/dev/null 2>&1 || \
       python3 -m pip install --break-system-packages --user --upgrade pip setuptools wheel >/dev/null 2>&1; then
      _ok "pip, setuptools, and wheel updated"
    else
      _warn "Failed to update pip tools, continuing anyway..."
    fi

    # 사용자 패키지 설치
    _install_pip_package "toast-cli"

    # Update timestamp
    date +%s > "$PIP_TIMESTAMP_FILE"
  else
    _skip "PIP packages update (last update was less than 6 hours ago)"
  fi
else
  _skip "Python3 not found"
fi

# Step 7: OS별 시스템 설정
_progress "Configuring OS-specific settings..."

# macOS 설정
if [ "${OS_NAME}" == "darwin" ]; then
  # CLT 설치 여부는 xcode-select -p 로 확인 (xcode-select 바이너리는 macOS 기본 탑재)
  if ! xcode-select -p >/dev/null 2>&1; then
    _run "Installing Xcode Command Line Tools..."
    xcode-select --install
    _warn "Xcode CLT installer launched — complete the dialog, then re-run this script"
  else
    _skip "Xcode Command Line Tools already installed"
  fi

  # Rosetta 2 는 CLT 와 독립적으로 확인 (arm64 전용, oahd 데몬으로 설치 감지)
  if [ "${OS_ARCH}" == "arm64" ]; then
    if ! pgrep -q oahd; then
      _run "Installing Rosetta 2 for x86_64 compatibility..."
      if sudo softwareupdate --install-rosetta --agree-to-license; then
        _ok "Rosetta 2 installed"
      else
        _warn "Rosetta 2 install failed"
      fi
    else
      _skip "Rosetta 2 already installed"
    fi
  fi

  # ₩ -> ` 키 바인딩 설정
  if [ ! -f ~/Library/KeyBindings/DefaultkeyBinding.dict ]; then
    _download Library/KeyBindings/DefaultkeyBinding.dict darwin/DefaultkeyBinding.dict
    _ok "Korean keyboard won symbol (₩) mapped to backtick (\`)"
  else
    _skip "Keyboard binding already configured"
  fi

  # macOS 시스템 설정
  _download .macos macos
  if [ ! -f ~/.macos.backup ]; then
    _run "Applying macOS system preferences..."
    /bin/bash ~/.macos
    _backup ~/.macos
    _ok "macOS system preferences applied"
  else
    if [ -f ~/.dotfiles/macos ] && [ "$(_md5 ~/.dotfiles/macos)" != "$(_md5 ~/.macos.backup)" ]; then
      _run "Updating macOS system preferences..."
      /bin/bash ~/.macos
      _backup ~/.macos
      _ok "macOS system preferences updated"
    else
      _skip "macOS system preferences already applied"
    fi
  fi
fi

# Step 8: 셸 환경 설정
_progress "Installing ZSH and Oh My ZSH..."

# Oh My ZSH 설치
if [ ! -d ~/.oh-my-zsh ]; then
  _run "Installing Oh My ZSH..."
  RUNZSH=no CHSH=no /bin/bash -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" >/dev/null 2>&1 || true
  # 사후 검증: 설치 실패를 성공으로 보고하지 않는다
  if [ -d ~/.oh-my-zsh ]; then
    _ok "Oh My ZSH installed"
  else
    _warn "Oh My ZSH install failed (network issue?)"
  fi
else
  _skip "Oh My ZSH already installed"
fi

# 기본 셸을 ZSH로 변경 (oh-my-zsh 설치 여부와 별개로 체크)
if [[ "${SHELL}" != *"zsh"* ]]; then
  ZSH_PATH=$(command -v zsh)
  if [ -n "$ZSH_PATH" ]; then
    _run "Changing default shell to ZSH ($ZSH_PATH)..."

    # /etc/shells에 zsh가 등록되어 있는지 확인
    if ! grep -q "^${ZSH_PATH}$" /etc/shells 2>/dev/null; then
      echo "$ZSH_PATH" | sudo tee -a /etc/shells >/dev/null
    fi

    # chsh 실행 (권한 필요시 sudo 사용)
    if chsh -s "$ZSH_PATH" 2>/dev/null; then
      _ok "Default shell changed to ZSH"
    elif sudo chsh -s "$ZSH_PATH" "$USER"; then
      _ok "Default shell changed to ZSH (with sudo)"
    else
      _warn "Failed to change default shell to ZSH"
    fi
  else
    _error "ZSH not found in PATH"
  fi
else
  _skip "Default shell is already ZSH"
fi

# Step 9: 테마 및 UI 설정
_progress "Installing theme and UI settings..."

# Dracula 테마 디렉토리 생성
if [ ! -d ~/.dracula ]; then
  mkdir -p ~/.dracula
fi

# Dracula ZSH 테마 설치
if [ ! -d ~/.dracula/zsh ]; then
  _run "Installing Dracula theme for ZSH..."
  if _retry "Dracula ZSH theme clone" git clone https://github.com/dracula/zsh.git ~/.dracula/zsh; then
    _ok "Dracula ZSH theme installed"
  else
    _warn "Failed to clone Dracula ZSH theme (network issue?)"
  fi
else
  _skip "Dracula ZSH theme already installed"
fi

# oh-my-zsh 테마 디렉토리에 링크 생성
if [ -d ~/.oh-my-zsh/themes ] && [ -d ~/.dracula/zsh ]; then
  if [ ! -L ~/.oh-my-zsh/themes/dracula.zsh-theme ]; then
    ln -sf ~/.dracula/zsh/dracula.zsh-theme ~/.oh-my-zsh/themes/dracula.zsh-theme
    _ok "Dracula theme linked to Oh My ZSH"
  else
    _skip "Dracula theme already linked"
  fi
elif [ ! -d ~/.oh-my-zsh/themes ]; then
  _skip "Oh My ZSH not found"
fi

# macOS 전용: iTerm2 Dracula 테마
if [ "${OS_NAME}" == "darwin" ]; then
  if [ ! -d ~/.dracula/iterm ]; then
    _run "Installing Dracula theme for iTerm2..."
    if _retry "Dracula iTerm2 theme clone" git clone https://github.com/dracula/iterm.git ~/.dracula/iterm; then
      mkdir -p ~/Library/Application\ Support/iTerm2
      ln -sf ~/.dracula/iterm/Dracula.itermcolors ~/Library/Application\ Support/iTerm2/Dracula.itermcolors
      _ok "Dracula iTerm2 theme installed"
    else
      _warn "Failed to clone Dracula iTerm2 theme (network issue?)"
    fi
  else
    _skip "Dracula iTerm2 theme already installed"
  fi
fi

if [ "${OS_NAME}" == "darwin" ]; then
  # iTerm2 설정 파일
  _download .iterm2/profiles.json iterm2/profiles.json

  # Ghostty 설정 파일
  _download .config/ghostty/config ghostty/config
fi

# Step 10: 사용자 설정 파일 적용
_progress "Applying user configuration files..."

# 셸 설정 파일들
_run "Downloading shell configuration files..."
_download .bashrc bashrc
_download .profile profile
_download .aliases aliases
_download .vimrc vimrc
_download .tmux.conf tmux.conf
_download .zshrc zshrc
_download .zprofile $OS_NAME/zprofile.$OS_ARCH.sh
_ok "Shell configuration files applied"

# Step 11: AI 도구 설정 (Claude Code, Kiro)
_progress "Setting up AI tools (Claude Code, Codex, Kiro)..."
_sync_vibe

# Success
_success

exit
}
