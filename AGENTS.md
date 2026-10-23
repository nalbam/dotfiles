# AGENTS.md

Guidance for Codex (and other AI agents) working in this repository. For a human-facing overview, see [README.md](./README.md).

## What this repo is

Machine setup and maintenance for macOS, WSL2, DGX Spark, EC2 (k3s nodes), Raspberry Pi and generic Ubuntu/Debian. `run.sh` bootstraps `~/.dotfiles` and runs `dot up`; `bin/dot` detects the platform, applies its profile and enabled add-on modules, and upgrades what is due on every run. Add-ons include the DGX Spark model stack (`stacks/dgx-spark`), monitoring, VibeMon, k3s and Docker.

`run.sh`, `bin/dot`, `lib/` and `modules/` are Bash and **must stay compatible with Bash 3.2** (macOS `/bin/bash`): no associative arrays, `${var,,}`, `mapfile` or `declare -A`. AI settings sync and stack helpers use Python 3.11+ standard libraries. `config/shell/aliases` and the zprofiles must work in both Bash and Zsh. **No build step, no package graph.**

## Entry points

| File | Role |
|------|------|
| `run.sh` | Bootstrap only: clone or download `~/.dotfiles`, then exec `bin/dot up` (`--vibe` → `dot vibe`). |
| `bin/dot` | CLI. Commands: `up`, `run`, `add`, `remove`, `list`, `status`, `doctor`, `platform`, `upgrade-system`, `vibe`, `@HOST`, and module CLIs such as `dot llm`. Never put it on `PATH`: `dot` belongs to Graphviz and other tools, and setup must not shadow commands a machine already has. |
| `lib/modules.sh` | Module contract and `DOT_MODULE_ORDER` (the execution order). |
| `modules/<name>.sh` | One module per file: `<name>::describe`, `<name>::up`, optional `supported`, `detect`, `status`, `cli`. |
| `profiles/<platform>` | Default modules per platform. |
| `config/shell/aliases` | All shell aliases and helper functions. |
| `packages/Brewfile.darwin`, `packages/Brewfile.linux` | Declarative package lists (read these — do not enumerate packages here). |
| `stacks/dgx-spark/` | Docker Compose model stack operated by the `llm`, `monitoring` and `vibemon` modules. |

**Before changing installer behavior, read `bin/dot`, `lib/` and the affected modules end to end.** Module order matters (e.g., `brew` installs nvm before `node` uses it).

## Public repository, private machines

This repository is public. Never commit host names, tailnet names, IP addresses, account or collector IDs, tokens, or user names of private machines. Put them in `~/.config/dotfiles/local.env`, `~/.config/dotfiles/hosts/<name>.env`, or a stack's runtime env file, and document only placeholders. Image names, labels and unit names that start with `dockpad` are kept on purpose: renaming them recreates running containers and services.

## Git profile switching (non-obvious)

Base `config/git/gitconfig` uses `includeIf` to select directory-specific identities. Read all `config/git/gitconfig*` files together when changing identity settings. The `git` module deploys every `gitconfig-*` file, so a new include needs only its file; a wrong email changes commit attribution.

## Platform-specific gotchas

- **macOS arm64**: Homebrew lives at `/opt/homebrew`. Rosetta 2 is auto-installed for x86_64 binaries. Never run `/usr/bin/git` before Command Line Tools exist (it opens a dialog).
- **macOS x86_64**: Homebrew at `/usr/local`.
- **DGX Spark**: DGX OS owns Docker, the NVIDIA runtime, drivers and kernel. `dot up` must not upgrade OS packages or restart Docker; GPU memory is shared with the host and a watchdog stops Flash when memory is low, so heavy work (Homebrew source builds) checks available memory first.
- **EC2 / k3s**: upgrades replace the k3s binary and restart its service; never re-run the installer for upgrades (it would rewrite flags and the node role).
- **Raspberry Pi (aarch64/armv7l)**: Homebrew is unavailable on 32-bit ARM; Node.js may build from source. The installer does not install global npm packages; do not recommend `sudo npm`.
- **zprofile scripts** must degrade gracefully when `brew` / `pyenv` / `nvm` are absent — they run early in shell init.

## Resilience contracts (keep these when editing lib/ and modules/)

- `dot_retry` network calls: at most 3 attempts, with 5s and 10s waits between attempts.
- Upgrade throttling: 6 h stamps in `~/.local/state/dotfiles/stamps/`; a module stamps only after its checked upgrade succeeded. Changed sources (Brewfile, macOS preferences, Spark stack, Neovim config) bypass the throttle via applied markers.
- File ops: MD5 check before overwrite; backup before replace; `~/.ssh/*`, `~/.aws/*` and `*.backup` get `chmod 600`.
- PIP fallback chain: `pip install` → `--user` → `--break-system-packages --user` → `sudo` (for PEP 668 systems).
- OS package upgrades only through `dot upgrade-system --yes`.
- Each module runs in a subshell; a failure stops only that module and is reported in the summary and exit status.

Do not remove these without a clear reason — they exist because of real failure modes on constrained platforms (Pi, locked-down corp machines, WSL, GPU servers).

## Aliases/helpers (source of truth: `config/shell/aliases`)

Don't duplicate the alias list here — read `config/shell/aliases` directly. When adding new helpers:

- Put them in `config/shell/aliases` (not `zshrc`), grouped by tool.
- Keep functions small; prefer POSIX-compatible syntax so `bashrc` can source them too.
- Preserve Korean keyboard aliases when refactoring.

## AI tool settings (claude/, codex/, opencode/, kiro/)

Edit repository sources, not deployed copies. `dot vibe` (and `run.sh --vibe`) deploys from the checkout that contains the running `bin/dot`, normally `~/.dotfiles`. See [AI Tools Sync](./README.md#ai-tools-sync) for targets, local-state exceptions, and deployment checks.

When the source Codex config selects `default_permissions`, sync owns approval and sandbox selection (`approval_policy`, `approvals_reviewer`, `default_permissions`, `sandbox_mode`, `sandbox_workspace_write`). These keys follow the repository, including removal of obsolete selectors. Other local settings keep their existing values.

Sync also owns `features.chronicle` and `features.local_thread_store_compression` when present in the source Codex config. Keep these under-development opt-ins `false` in the source; sync replaces the local value, including `true`. Preserve other local feature flags and session/memory data; do not suppress startup warnings globally.

Sync also owns `permissions.deny` and `autoMode` in `claude/settings.json` and `permissions` in `opencode/opencode.json`: the deployed value is replaced with the repository value. Claude Code checks each subcommand of a compound command separately, so write a deny rule for one subcommand; a rule that contains `|` never matches. A rule that mixes `*` with a trailing `:*` is a literal prefix and also never matches.

The root `AGENTS.md` guides work on this repository. `claude/CLAUDE.md` and `claude/rules/` are the global instructions; the generator combines them into `codex/AGENTS.md` and `opencode/AGENTS.md`. Keep them independent of machine paths and project-specific commands.

Hook ownership follows deployed script paths, not whole event arrays. Sync refreshes dotfiles-owned hook registrations while preserving VibeMon, romty, and user hooks. VibeMon scripts and Claude `statusline.py` belong to the VibeMon installer; old manifest entries must be released without deleting those files. Shared settings files must never be pruned wholesale. Generic Codex `tui.status_line` defaults belong here and preserve existing machine choices.

**`codex/AGENTS.md`, `codex/skills/` Markdown, and everything under `opencode/` are generated — do not edit directly.** Sources: `claude/CLAUDE.md` and `claude/rules/` for global instructions, `claude/skills/` for skills, `claude/agents/` for OpenCode subagents, and `claude/settings.json` deny rules for OpenCode shell permissions. Regenerate with `python3 scripts/gen-ai-tools.py` (verify with `--check`). Codex-only files like `agents/openai.yaml` are hand-maintained and preserved by the generator. OpenCode V2 reads only `AGENTS.md` instructions and registers every root-level `*.md` in a skills directory as a skill, so keep skill directories free of guide files. Tool-specific instructions must be adapted by the generator, not copied into the other tool's workflow.

For Codex and OpenCode instruction changes:

1. Edit global instructions in `claude/CLAUDE.md` and `claude/rules/`, shared skills in `claude/skills/`, subagents in `claude/agents/`, and Codex configuration in `codex/`.
2. Regenerate with `python3 scripts/gen-ai-tools.py` and run `python3 scripts/gen-ai-tools.py --check`.
3. Run `python3 -m unittest discover -s tests -p 'test_ai_tools.py'`, `bash -n run.sh bin/dot`, and `git diff --check`. Tests use temporary homes; no live deployment or remote push is required. Check referenced paths, instruction sections, and tool compatibility.
4. Deploy using the README procedure when deployment is in scope. Do not run the installer merely to validate documentation.

For installer, module, shell, stack, or platform changes, run `python3 -m unittest discover -s tests -p 'test_*.py'` and `bash -n` for the changed shell files (also `zsh -n` for shared shell startup files). Report skipped platform runtimes separately from passing tests.

## Working rules for agents

- Apply the ISO 24495-1 and ASD-STE100 writing principles in [the shared documentation workflow](./claude/skills/docs-sync/SKILL.md#작성-품질). Match the reader's task, preserve technical meaning, and verify examples against code. Do not claim full standard compliance from these checks alone.
- **Merge authority depends on the owner of the base repository.** In a repository owned by the authenticated user's account or the user's own organization `opspresso`, merge a PR/MR without asking when it is mergeable and required checks pass; push directly to the default branch only under the same checks and branch protection. In any other repository (other organization, other user, fork upstream), merge, enroll auto-merge, or push to the default branch only with the user's explicit permission for that PR/MR or push; otherwise report readiness and stop. Treat an unknown owner as not owned. This covers PR/MR merges, pushes to the default branch, and auto-merge enrollment.
- **Autonomously release and deploy within the requested task when verification shows no blocking issues.** Before any merge, default-branch push, release, or deploy, confirm the exact commit passes required checks, CI, and reviews; resolve conflicts and verify the destination and impact. Do not treat pending or missing results as success or bypass branch protection, required reviews, environment approvals, or tool restrictions. Honor read-only requests and explicit stopping points.
- Fix and recheck issues within scope before continuing. Ask the user only when their decision or authority is required. Verify the released version, artifacts, deployment state, and normal operation before reporting completion.
- After release completion, clean up the task's local and remote branches. Confirm their changes are merged and no unmerged commits, uncommitted changes, or other worktrees need them. Preserve the default branch, unrelated branches, and user changes.
- **Changes are live the next time `dot up` runs on any machine,** including servers and the DGX Spark. Test locally before recommending risky changes.
- **Check every platform a change touches** (`macos`, `wsl`, `dgx-spark`, `ec2`, `rpi`, `linux`); review each module's `supported` function and both `darwin`/`linux` sources.
- **Prefer data over logic:** edit `config/`, `packages/Brewfile.*`, `profiles/` or `stacks/` before adding code to a module, and add a module before adding code to `bin/dot`.

For components, the run sequence and failure diagnosis, see [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).
