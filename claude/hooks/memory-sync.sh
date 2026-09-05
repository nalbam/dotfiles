#!/usr/bin/env bash
# Sync Claude Code auto-memory across machines via the private
# nalbam/claude-memory repo. Deployed to ~/.claude/hooks/ by run.sh --vibe.
#
# Usage:
#   memory-sync.sh start          # SessionStart hook: link current project, sync in background
#   memory-sync.sh end            # SessionEnd hook: commit and push in background
#   memory-sync.sh link <path>..  # manually link/migrate specific project dirs (sync runs inline)
#
# Layout: ~/.claude-memory/<path-relative-to-HOME> holds the memory files;
# ~/.claude/projects/<slug>/memory is a symlink into it. The slug embeds the
# absolute project path, which differs per machine (/Users vs /home), so the
# HOME-relative path is the canonical cross-machine key.
#
# Hooks detach clone/link/sync work so first-run network access cannot exceed
# the session hook timeout. The link is available once bootstrap finishes.

set -u

MEMORY_REPO="git@github.com:nalbam/claude-memory.git"
MEMORY_ROOT="${HOME}/.claude-memory"
PROJECTS_ROOT="${HOME}/.claude/projects"
LOCK_DIR="${MEMORY_ROOT}/.sync.lock"
LOCK_STALE_MIN=5

# Absolute path to this script, for re-invoking ourselves detached.
SELF="$0"
case "${SELF}" in
  /*) ;;
  *) SELF="$(pwd)/${SELF}" ;;
esac

ensure_repo() {
  [ -d "${MEMORY_ROOT}/.git" ] && return 0
  git clone --quiet "${MEMORY_REPO}" "${MEMORY_ROOT}" 2>/dev/null
}

# Only one sync may touch the repo at a time — detached syncs from several
# sessions can overlap. A lock left behind by a killed sync is reclaimed after
# LOCK_STALE_MIN minutes so the repo never stays wedged.
acquire_lock() {
  mkdir "${LOCK_DIR}" 2>/dev/null && return 0
  [ -n "$(find "${LOCK_DIR}" -maxdepth 0 -mmin "+${LOCK_STALE_MIN}" 2>/dev/null)" ] || return 1
  rmdir "${LOCK_DIR}" 2>/dev/null
  mkdir "${LOCK_DIR}" 2>/dev/null
}

# Commit local changes first so the tree is clean, then converge with remote.
# Network failures are tolerated silently — offline sessions must never block.
# A lock we cannot take means another sync is already converging; skip.
sync_repo() {
  local diff_status
  acquire_lock || return 0
  trap 'rmdir "${LOCK_DIR}" 2>/dev/null' EXIT INT TERM

  if [ -d "${MEMORY_ROOT}/.git/rebase-merge" ] || [ -d "${MEMORY_ROOT}/.git/rebase-apply" ] ||
     [ -f "${MEMORY_ROOT}/.git/MERGE_HEAD" ] || [ -f "${MEMORY_ROOT}/.git/CHERRY_PICK_HEAD" ]; then
    return 1
  fi

  git -C "${MEMORY_ROOT}" add -A -- . ':(glob,exclude)**/*.jsonl' 2>/dev/null || return 1
  git -C "${MEMORY_ROOT}" diff --cached --quiet 2>/dev/null
  diff_status=$?
  if [ "$diff_status" -eq 1 ]; then
    git -C "${MEMORY_ROOT}" commit --quiet \
      -m "sync: $(hostname) $(date '+%Y-%m-%d %H:%M:%S')" 2>/dev/null || return 1
  elif [ "$diff_status" -ne 0 ]; then
    return 1
  fi
  git -C "${MEMORY_ROOT}" pull --rebase --autostash --quiet 2>/dev/null || return 1
  git -C "${MEMORY_ROOT}" push --quiet 2>/dev/null || return 1

  trap - EXIT INT TERM
  rmdir "${LOCK_DIR}" 2>/dev/null
}

# Re-run ourselves as `sync` in a double-forked, nohup'd child: the inner
# subshell exits immediately, so the git work is orphaned to init and outlives
# both this hook and the Claude Code process that spawned it.
detach_sync() {
  ( nohup bash "${SELF}" "$@" >/dev/null 2>&1 & ) </dev/null >/dev/null 2>&1
}

# Link ~/.claude/projects/<slug>/memory -> ~/.claude-memory/<key> for one
# project. An existing real memory dir is migrated into the repo (files
# already in the repo win on name conflicts; the original dir is kept as
# memory.backup).
link_project() {
  local project_path="$1" key slug target link

  case "${project_path}" in
    "${HOME}"/*) key="${project_path#"${HOME}"/}" ;;
    *) return 0 ;;  # outside HOME: no stable cross-machine key, skip
  esac
  case "/${key}/" in
    */../* | */./*) return 1 ;;
  esac

  slug=$(printf '%s' "${project_path}" | sed 's/[^a-zA-Z0-9]/-/g')
  target="${MEMORY_ROOT}/${key}"
  link="${PROJECTS_ROOT}/${slug}/memory"

  if [ -L "${link}" ]; then
    [ "$(readlink "${link}")" = "${target}" ] && return 0
    rm -f "${link}" || return 1
  elif [ -d "${link}" ]; then
    # Never replace an earlier migration backup or move data after a failed copy.
    [ ! -e "${link}.backup" ] && [ ! -L "${link}.backup" ] || return 1
    mkdir -p "${target}" || return 1
    cp -an "${link}/." "${target}/" 2>/dev/null || return 1
    mv "${link}" "${link}.backup" || return 1
  fi

  mkdir -p "${target}" "${PROJECTS_ROOT}/${slug}" || return 1
  ln -s "${target}" "${link}"
}

case "${1:-}" in
  start)
    detach_sync bootstrap "${CLAUDE_PROJECT_DIR:-$(pwd)}"
    ;;
  bootstrap)
    ensure_repo || exit 1
    link_project "$2" || exit 1
    sync_repo || exit 1
    ;;
  end)
    [ -d "${MEMORY_ROOT}/.git" ] || exit 0
    detach_sync sync
    ;;
  sync)
    [ -d "${MEMORY_ROOT}/.git" ] || exit 0
    sync_repo || exit 1
    ;;
  link)
    shift
    ensure_repo || exit 1
    for p in "$@"; do
      # Resolve to an absolute path; a project deleted locally may still have
      # memory worth migrating, so accept absolute paths that no longer exist.
      if abs=$(cd "$p" 2>/dev/null && pwd); then
        link_project "${abs}" || exit 1
      else
        case "$p" in
          /*) link_project "$p" || exit 1 ;;
          *) echo "skip: $p (not found and not absolute)" >&2 ;;
        esac
      fi
    done
    sync_repo || exit 1
    ;;
  *)
    echo "usage: $0 {start|end|link <path>...}" >&2
    exit 1
    ;;
esac

exit 0
