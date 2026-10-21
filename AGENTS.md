# AGENTS.md

Guidance for Codex (and other AI agents) working in this repository. For a human-facing overview, see [README.md](./README.md).

## What this repo is

Cross-platform dotfiles installer. A single shell script (`run.sh`) detects the OS/architecture and provisions a consistent dev environment: SSH keys, Git config, package managers, shell, terminals, and AI tool settings.

The installer (`run.sh`) is Bash; AI settings sync uses Python 3.11+ standard libraries in `scripts/sync-ai-tools.py`. `zshrc` and `bashrc` configure their respective shells. Shared `aliases` and `zprofile.*` files must work in both Bash and Zsh; prefer POSIX-compatible syntax for shared helpers. **No build step, no package graph**.

## Entry points

| File | Role |
|------|------|
| `run.sh` | Main installer — 11 ordered steps (see [Installation Flow](./docs/ARCHITECTURE.md#installation-flow)). Source of truth for what gets installed and in what order. |
| `run.ps1` | Windows PowerShell setup for Git/Vim links and basic packages; does not sync AI settings. |
| `aliases` | All shell aliases and helper functions. Sourced from `zshrc`/`bashrc`. |
| `darwin/Brewfile`, `linux/Brewfile` | Declarative package lists (read these — do not enumerate packages here). |

**Before changing installer behavior, read `run.sh` end-to-end.** The steps are interdependent (e.g., Step 5 bootstraps Homebrew before Step 6 uses it).

`run.sh --vibe` runs **only the AI tools sync step** (step 11 of 11).

## Git profile switching (non-obvious)

Base `gitconfig` uses `includeIf` to select directory-specific identities. Read all `gitconfig*` files together when changing identity settings, and keep the Step 4 deployment list in sync with the includes; a wrong email changes commit attribution.

## Platform-specific gotchas

- **macOS arm64**: Homebrew lives at `/opt/homebrew`. Rosetta 2 is auto-installed for x86_64 binaries.
- **macOS x86_64**: Homebrew at `/usr/local`.
- **Raspberry Pi (aarch64/armv7l)**: Homebrew and Node.js bootstrapping can require slow source builds. The installer does not install global npm packages; do not recommend `sudo npm`.
- **Ubuntu/WSL**: uses the Linux/APT path. The installer attempts Homebrew installation and warns if it remains unavailable.
- **zprofile scripts** must degrade gracefully when `brew` / `pyenv` / `nvm` are absent — they run early in shell init.

## Resilience contracts (keep these when editing run.sh)

- `_retry` network calls: at most 3 attempts, with 5s and 10s waits between attempts.
- Update throttling: 6 h timestamps in `~/.toast/last_update_*`; Claude Code advances its marker only after a successful update. Brewfile changes bypass the throttle (`brew bundle` runs whenever the Brewfile differs from the last successfully bundled copy at `~/.Brewfile`).
- File ops: MD5 check before overwrite; sensitive files (`~/.ssh/*`, `~/.aws/*`, `*.backup`) get `chmod 600`.
- PIP fallback chain: `pip install` → `--user` → `--break-system-packages --user` → `sudo` (for PEP 668 systems).
- Backup-before-overwrite on user config files.

Do not remove these without a clear reason — they exist because of real failure modes on constrained platforms (Pi, locked-down corp machines, WSL).

## Aliases/helpers (source of truth: `aliases`)

Don't duplicate the alias list here — read `aliases` directly. When adding new helpers:

- Put them in `aliases` (not `zshrc`), grouped by tool.
- Keep functions small; prefer POSIX-compatible syntax so `bashrc` can source them too.
- Preserve Korean keyboard aliases when refactoring.

## AI tool settings (claude/, codex/, opencode/, kiro/)

Edit repository sources, not deployed copies. `run.sh --vibe` reads from `~/.dotfiles`, even when invoked from another checkout. See [AI Tools Sync](./README.md#ai-tools-sync) for targets, local-state exceptions, and deployment checks.

When the source Codex config selects `default_permissions`, sync owns approval and sandbox selection (`approval_policy`, `approvals_reviewer`, `default_permissions`, `sandbox_mode`, `sandbox_workspace_write`). These keys follow the repository, including removal of obsolete selectors. Other local settings keep their existing values.

Sync also owns `features.chronicle` and `features.local_thread_store_compression` when present in the source Codex config. Keep these under-development opt-ins `false` in the source; sync replaces the local value, including `true`. Preserve other local feature flags and session/memory data; do not suppress startup warnings globally.

Sync also owns `permissions.deny` and `autoMode` in `claude/settings.json` and `permissions` in `opencode/opencode.json`: the deployed value is replaced with the repository value. Claude Code checks each subcommand of a compound command separately, so write a deny rule for one subcommand; a rule that contains `|` never matches. A rule that mixes `*` with a trailing `:*` is a literal prefix and also never matches.

The root `AGENTS.md` guides work on this repository. `claude/CLAUDE.md` and `claude/rules/` are the global instructions; the generator combines them into `codex/AGENTS.md` and `opencode/AGENTS.md`. Keep them independent of machine paths and project-specific commands.

Hook ownership follows deployed script paths, not whole event arrays. Sync refreshes dotfiles-owned hook registrations while preserving VibeMon, romty, and user hooks. VibeMon scripts and Claude `statusline.py` belong to the VibeMon installer; old manifest entries must be released without deleting those files. Shared settings files must never be pruned wholesale. Generic Codex `tui.status_line` defaults belong here and preserve existing machine choices.

**`codex/AGENTS.md`, `codex/skills/` Markdown, and everything under `opencode/` are generated — do not edit directly.** Sources: `claude/CLAUDE.md` and `claude/rules/` for global instructions, `claude/skills/` for skills, `claude/agents/` for OpenCode subagents, and `claude/settings.json` deny rules for OpenCode shell permissions. Regenerate with `python3 scripts/gen-ai-tools.py` (verify with `--check`). Codex-only files like `agents/openai.yaml` are hand-maintained and preserved by the generator. OpenCode V2 reads only `AGENTS.md` instructions and registers every root-level `*.md` in a skills directory as a skill, so keep skill directories free of guide files. Tool-specific instructions must be adapted by the generator, not copied into the other tool's workflow.

For Codex and OpenCode instruction changes:

1. Edit global instructions in `claude/CLAUDE.md` and `claude/rules/`, shared skills in `claude/skills/`, subagents in `claude/agents/`, and Codex configuration in `codex/`.
2. Regenerate with `python3 scripts/gen-ai-tools.py` and run `python3 scripts/gen-ai-tools.py --check`.
3. Run `python3 scripts/test_ai_tools.py`, `bash -n run.sh`, and `git diff --check`. Tests use temporary homes; no live deployment or remote push is required. Check referenced paths, instruction sections, and tool compatibility.
4. Deploy using the README procedure when deployment is in scope. Do not run the installer merely to validate documentation.

For installer, shell, or platform changes, run `python3 -m unittest discover -s scripts -p 'test_*.py'` and syntax checks for the changed shell files. Report skipped platform runtimes separately from passing tests.

## Working rules for agents

- Apply the ISO 24495-1 and ASD-STE100 writing principles in [the shared documentation workflow](./claude/skills/docs-sync/SKILL.md#작성-품질). Match the reader's task, preserve technical meaning, and verify examples against code. Do not claim full standard compliance from these checks alone.
- **Merge authority depends on the owner of the base repository.** In a repository owned by the authenticated user's account or the user's own organization `opspresso`, merge a PR/MR without asking when it is mergeable and required checks pass; push directly to the default branch only under the same checks and branch protection. In any other repository (other organization, other user, fork upstream), merge, enroll auto-merge, or push to the default branch only with the user's explicit permission for that PR/MR or push; otherwise report readiness and stop. Treat an unknown owner as not owned. This covers PR/MR merges, pushes to the default branch, and auto-merge enrollment.
- **Autonomously release and deploy within the requested task when verification shows no blocking issues.** Before any merge, default-branch push, release, or deploy, confirm the exact commit passes required checks, CI, and reviews; resolve conflicts and verify the destination and impact. Do not treat pending or missing results as success or bypass branch protection, required reviews, environment approvals, or tool restrictions. Honor read-only requests and explicit stopping points.
- Fix and recheck issues within scope before continuing. Ask the user only when their decision or authority is required. Verify the released version, artifacts, deployment state, and normal operation before reporting completion.
- After release completion, clean up the task's local and remote branches. Confirm their changes are merged and no unmerged commits, uncommitted changes, or other worktrees need them. Preserve the default branch, unrelated branches, and user changes.
- **Shell changes are live the next time `run.sh` runs on any machine.** Test locally before recommending risky changes.
- **Check both `darwin/` and `linux/` paths** when touching platform logic — one branch is easy to miss.
- **Prefer editing `aliases` or `Brewfile` over adding logic to `run.sh`.** The installer should stay declarative.

For the directory tree, installation flow sequence, and architecture diagrams, see [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).
