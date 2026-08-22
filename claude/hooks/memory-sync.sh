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
# The hooks must not stall the session: SessionStart holds startup until the
# hook returns, and SessionEnd is awaited inside Claude Code's shutdown path.
# So the network work is detached (see detach_sync) and the hook returns at
# once; only the local symlink work stays inline.

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
  acquire_lock || return 0
  trap 'rmdir "${LOCK_DIR}" 2>/dev/null' EXIT INT TERM

  git -C "${MEMORY_ROOT}" add -A 2>/dev/null
  if ! git -C "${MEMORY_ROOT}" diff --cached --quiet 2>/dev/null; then
    git -C "${MEMORY_ROOT}" commit --quiet \
      -m "sync: $(hostname) $(date '+%Y-%m-%d %H:%M:%S')" 2>/dev/null
  fi
  git -C "${MEMORY_ROOT}" pull --rebase --autostash --quiet 2>/dev/null
  git -C "${MEMORY_ROOT}" push --quiet 2>/dev/null

  trap - EXIT INT TERM
  rmdir "${LOCK_DIR}" 2>/dev/null
}

# Re-run ourselves as `sync` in a double-forked, nohup'd child: the inner
# subshell exits immediately, so the git work is orphaned to init and outlives
# both this hook and the Claude Code process that spawned it.
detach_sync() {
  ( nohup "${SELF}" sync >/dev/null 2>&1 & ) </dev/null >/dev/null 2>&1
}

# Link ~/.claude/projects/<slug>/memory -> ~/.claude-memory/<key> for one
# project. An existing real memory dir is migrated into the repo (files
# already in the repo win on name conflicts; the original dir is kept as
# memory.backup).
link_project() {
  project_path="$1"

  case "${project_path}" in
    "${HOME}"/*) key="${project_path#"${HOME}"/}" ;;
    *) return 0 ;;  # outside HOME: no stable cross-machine key, skip
  esac

  slug=$(printf '%s' "${project_path}" | sed 's/[^a-zA-Z0-9]/-/g')
  target="${MEMORY_ROOT}/${key}"
  link="${PROJECTS_ROOT}/${slug}/memory"

  if [ -L "${link}" ]; then
    [ "$(readlink "${link}")" = "${target}" ] && return 0
    rm -f "${link}"
  elif [ -d "${link}" ]; then
    mkdir -p "${target}"
    cp -an "${link}/." "${target}/" 2>/dev/null
    rm -rf "${link}.backup"
    mv "${link}" "${link}.backup"
  fi

  mkdir -p "${target}" "${PROJECTS_ROOT}/${slug}"
  ln -s "${target}" "${link}"
}

case "${1:-}" in
  start)
    # The clone is a one-time cost on a fresh machine and must finish before
    # anything links into the repo, so it stays inline.
    ensure_repo || exit 0
    link_project "${CLAUDE_PROJECT_DIR:-$(pwd)}"
    detach_sync
    ;;
  end)
    [ -d "${MEMORY_ROOT}/.git" ] || exit 0
    detach_sync
    ;;
  sync)
    [ -d "${MEMORY_ROOT}/.git" ] || exit 0
    sync_repo
    ;;
  link)
    shift
    ensure_repo || exit 0
    for p in "$@"; do
      # Resolve to an absolute path; a project deleted locally may still have
      # memory worth migrating, so accept absolute paths that no longer exist.
      if abs=$(cd "$p" 2>/dev/null && pwd); then
        link_project "${abs}"
      else
        case "$p" in
          /*) link_project "$p" ;;
          *) echo "skip: $p (not found and not absolute)" >&2 ;;
        esac
      fi
    done
    sync_repo
    ;;
  *)
    echo "usage: $0 {start|end|link <path>...}" >&2
    exit 1
    ;;
esac

exit 0
