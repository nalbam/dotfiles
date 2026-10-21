# shellcheck shell=bash
# Keeps $DOT_HOME current. The bootstrap may install from an archive when Git
# is not usable yet (fresh macOS without Command Line Tools, minimal Linux);
# the archive is converted into a Git checkout once Git works.

# On macOS the /usr/bin/git stub opens an installer dialog when the Command
# Line Tools are missing, so it must not be executed in that state.
dot_git_usable() {
  dot_has git || return 1
  if [ "$(uname -s)" = Darwin ] && [ "$(command -v git)" = /usr/bin/git ]; then
    xcode-select -p >/dev/null 2>&1 || return 1
  fi
}

# Returns 0 when unchanged, 3 when the checkout changed (the caller restarts so
# the rest of the run uses the new code), and 0 with a warning on failure so an
# offline machine still converges with its current files.
dot_repo_sync() {
  local before after
  if ! dot_git_usable; then
    dot_skip "Git is not usable yet; keeping the current files"
    return 0
  fi

  if [ ! -d "$DOT_HOME/.git" ]; then
    dot_run "Converting $DOT_HOME into a Git checkout"
    if git -C "$DOT_HOME" init -q &&
       git -C "$DOT_HOME" remote add origin "$DOT_REPO_URL" &&
       dot_retry "Fetch" git -C "$DOT_HOME" fetch -q origin main &&
       git -C "$DOT_HOME" checkout -q -B main --force origin/main &&
       git -C "$DOT_HOME" branch -q --set-upstream-to=origin/main main; then
      dot_ok "Checkout tracks origin/main"
      return 3
    fi
    rm -rf "$DOT_HOME/.git"
    dot_warn "Could not convert $DOT_HOME into a Git checkout; continuing with the current files"
    return 0
  fi

  before=$(git -C "$DOT_HOME" rev-parse HEAD 2>/dev/null)
  if dot_retry "Pull" git -C "$DOT_HOME" pull -q --ff-only; then
    after=$(git -C "$DOT_HOME" rev-parse HEAD 2>/dev/null)
    if [ "$before" != "$after" ]; then
      dot_ok "Updated $(git -C "$DOT_HOME" rev-parse --short "$before")..$(git -C "$DOT_HOME" rev-parse --short "$after")"
      return 3
    fi
    dot_ok "Up to date ($(git -C "$DOT_HOME" rev-parse --short HEAD))"
    return 0
  fi
  # Local commits or network failures must not block the rest of the run.
  dot_warn "Pull failed; continuing with the current checkout (check: git -C $DOT_HOME status)"
  return 0
}
