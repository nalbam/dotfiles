# AGENTS.md

Guidance for Codex (and other AI agents) working in this repository. For a human-facing overview, see [README.md](./README.md).

## What this repo is

Cross-platform dotfiles installer. A single shell script (`run.sh`) detects the OS/architecture and provisions a consistent dev environment: SSH keys, Git config, package managers, shell, terminals, and AI tool settings.

The installer (`run.sh`) is plain bash; AI settings sync uses Python 3.11+ standard libraries in `scripts/sync-ai-tools.py`. Files sourced by interactive shells (`aliases`, `zshrc`/`bashrc`, `zprofile.*`) stay POSIX-compatible so both bash and zsh can source them. **No build step, no package graph**.

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

Base `gitconfig` uses `includeIf` to select directory-specific email/signing profiles. Read `gitconfig`, `gitconfig-nalbam`, and `gitconfig-bruce` together when changing identity settings; a wrong email silently changes commit attribution.

## Platform-specific gotchas

- **macOS arm64**: Homebrew lives at `/opt/homebrew`. Rosetta 2 is auto-installed for x86_64 binaries.
- **macOS x86_64**: Homebrew at `/usr/local`.
- **Raspberry Pi (aarch64/armv7l)**: Homebrew is optional (ARM compile cost). npm globals may need `sudo`. Skip heavy packages when possible.
- **WSL**: detected as Linux x86_64. Homebrew optional.
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

## AI tool settings (claude/, codex/, kiro/)

Edit repository sources, not deployed copies. `run.sh --vibe` reads from `~/.dotfiles`, even when invoked from another checkout. See [AI Tools Sync](./README.md#ai-tools-sync) for targets, local-state exceptions, and deployment checks.

The root `AGENTS.md` guides work on this repository. `codex/AGENTS.md` is the global template deployed to `~/.codex/AGENTS.md`; keep it independent of machine paths and project-specific commands.

Auto-memory sync belongs to Claude Code: see `claude/hooks/memory-sync.sh` and its registration in `claude/settings.json`. Do not treat these as Codex hooks or transcript sync.

**`codex/skills/*/SKILL.md` and mirrored Markdown references are generated — do not edit directly.** `claude/skills/` is the single source; regenerate with `python3 scripts/gen-codex-skills.py` (verify with `--check`). Codex-only files like `agents/openai.yaml` are hand-maintained and preserved by the generator. Tool-specific instructions must be adapted by the generator, not copied into the other tool's workflow.

For Codex instruction changes:

1. Edit global instructions in `codex/AGENTS.md`, shared skills in `claude/skills/`, and Codex configuration in `codex/`.
2. Regenerate changed skills and run `python3 scripts/gen-codex-skills.py --check`.
3. Run `python3 scripts/test_ai_tools.py`, `bash -n run.sh claude/hooks/memory-sync.sh`, and `git diff --check`. Tests use temporary homes and fake Git commands; no live deployment or remote push is required. Check referenced paths, instruction sections, and tool compatibility.
4. Deploy using the README procedure when deployment is in scope. Do not run the installer merely to validate documentation.

## Working rules for agents

- **Do not commit or push without explicit user instruction.** Global rule, but especially important here — this repo drives the user's entire environment.
- **Shell changes are live the next time `run.sh` runs on any machine.** Test locally before recommending risky changes.
- **Check both `darwin/` and `linux/` paths** when touching platform logic — one branch is easy to miss.
- **Prefer editing `aliases` or `Brewfile` over adding logic to `run.sh`.** The installer should stay declarative.

For the directory tree, installation flow sequence, and architecture diagrams, see [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).
