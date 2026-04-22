# CLAUDE.md

Guidance for Claude Code (and other AI agents) working in this repository. For a human-facing overview, see [README.md](./README.md).

## What this repo is

Cross-platform dotfiles installer. A single shell script (`run.sh`) detects the OS/architecture and provisions a consistent dev environment: SSH keys, Git config, package managers, shell, terminals, and AI tool settings.

Everything is POSIX shell — **no bashisms, no build step, no package graph**. Changes land by editing scripts/config files and re-running `run.sh` (or `vv` for AI settings only).

## Entry points

| File | Role |
|------|------|
| `run.sh` | Main installer — 11 ordered steps (see §Installation flow). Source of truth for what gets installed and in what order. |
| `run.ps1` | Windows PowerShell equivalent. |
| `aliases` | All shell aliases and helper functions. Sourced from `zshrc`/`bashrc`. |
| `darwin/Brewfile`, `linux/Brewfile` | Declarative package lists (read these — do not enumerate packages here). |

**Before changing installer behavior, read `run.sh` end-to-end.** The steps are interdependent (e.g., Step 5 bootstraps Homebrew before Step 6 uses it).

## Installation flow (run.sh)

1. OS/arch detection (`darwin`/`linux`/`mingw64` × `arm64`/`x86_64`/`aarch64`/`armv7l`)
2. Directory scaffolding + SSH key generation (RSA + ED25519)
3. Clone/update dotfiles repo to `~/.dotfiles`
4. Deploy SSH/AWS/Git config templates
5. Package manager setup (APT for Linux, Homebrew install)
6. Package installation (Homebrew, NPM, PIP) — version-aware, skipped if up to date
7. OS-specific settings (macOS: Xcode CLT, `.macos` system preferences)
8. ZSH + Oh My ZSH install
9. Theme/UI (Dracula, iTerm2 profile)
10. Deploy user config files (`~/.zshrc`, `~/.aliases`, etc.)
11. AI tools sync (`claude/` → `~/.claude/`, `kiro/` → `~/.kiro/`)

`run.sh --vibe` (or the `vv` alias) runs **only step 11**.

## Repository layout

```
run.sh / run.ps1          # installers
aliases, zshrc, bashrc    # shell config
profile, vimrc, tmux.conf # tool config
gitconfig                 # base (sets me@nalbam.com)
gitconfig-nalbam          # personal profile
gitconfig-bruce           # work profile
macos                     # macOS system-pref script

darwin/                   # macOS
  Brewfile
  DefaultkeyBinding.dict  # Korean ₩ → backtick remap
  zprofile.arm64.sh       # Homebrew at /opt/homebrew
  zprofile.x86_64.sh      # Homebrew at /usr/local
linux/                    # Linux (per-arch zprofile.*.sh)
ssh/, aws/                # config templates
iterm2/, ghostty/         # terminal profiles

claude/                   # synced to ~/.claude/
  CLAUDE.md, settings.json, statusline.py
  agents/ hooks/ rules/ skills/
kiro/                     # synced to ~/.kiro/
  agents/ hooks/

docs/ARCHITECTURE.md      # diagrams + deeper notes
```

## Git profile switching (non-obvious)

Base `gitconfig` uses `includeIf` to swap email/signing by directory:

- `~/workspace/github.com/nalbam/`, `~/workspace/github.com/opspresso/` → `gitconfig-nalbam`
- `~/workspace/github-emu.com/`, `~/workspace/github.dev.kr.krpay.io/`, `~/workspace/github.com/karrot-emu/`, `~/workspace/github.com/daangn/` → `gitconfig-bruce`
- Otherwise → base `me@nalbam.com`

When editing `gitconfig*`, check all three files stay consistent. A wrong email will silently commit under the wrong identity.

## Platform-specific gotchas

- **macOS arm64**: Homebrew lives at `/opt/homebrew`. Rosetta 2 is auto-installed for x86_64 binaries.
- **macOS x86_64**: Homebrew at `/usr/local`.
- **Raspberry Pi (aarch64/armv7l)**: Homebrew is optional (ARM compile cost). npm globals may need `sudo`. Skip heavy packages when possible.
- **WSL**: detected as Linux x86_64. Homebrew optional.
- **zprofile scripts** must degrade gracefully when `brew` / `pyenv` / `nvm` are absent — they run early in shell init.

## Resilience contracts (keep these when editing run.sh)

- Network calls: exponential backoff, max 3 retries (5s → 10s → 20s).
- Update throttling: APT / Homebrew / NPM / PIP / Claude update once per 12 h; timestamps in `~/.toast/last_update_*`.
- File ops: MD5 check before overwrite; sensitive files (`~/.ssh/*`, `~/.aws/*`, `*.backup`) get `chmod 600`.
- PIP fallback chain: `pip install` → `--user` → `--break-system-packages --user` → `sudo` (for PEP 668 systems).
- Backup-before-overwrite on user config files.

Do not remove these without a clear reason — they exist because of real failure modes on constrained platforms (Pi, locked-down corp machines, WSL).

## Aliases/helpers (source of truth: `aliases`)

Don't duplicate the alias list here — read `aliases` directly. When adding new helpers:

- Put them in `aliases` (not `zshrc`), grouped by tool.
- Keep functions small; prefer POSIX-compatible syntax so `bashrc` can source them too.
- Toast CLI is the central workspace manager — `c`, `m`, `x`, `g`, `r`, `e`, `d`, `p`, `ssm`, `tu`, `tt` all route through it.
- Korean keyboard aliases exist (`ㅊ`, `ㅊㅇ`, `ㅅㅅ`, `ㅍㅍ`) — preserve them when refactoring.

## AI tool settings (claude/, kiro/)

These directories are the **source**; `~/.claude/` and `~/.kiro/` are deployment targets. Never edit the deployed copies and expect them to persist — the next `vv` run overwrites changed files (MD5-compared).

When adding a new Claude Code agent/skill/rule:

1. Create the file under `claude/agents/` · `claude/skills/<name>/` · `claude/rules/`.
2. If it needs permissions or hooks, edit `claude/settings.json`.
3. Run `vv` to deploy. No installer re-run needed.

## Working rules for agents

- **Do not commit or push without explicit user instruction.** Global rule, but especially important here — this repo drives the user's entire environment.
- **Shell changes are live the next time `run.sh` runs on any machine.** Test locally before recommending risky changes.
- **Read the whole file before editing** (`run.sh` is ~600 lines but tightly sequenced).
- **Check both `darwin/` and `linux/` paths** when touching platform logic — one branch is easy to miss.
- **Prefer editing `aliases` or `Brewfile` over adding logic to `run.sh`.** The installer should stay declarative.
- **POSIX-compliant** shell only. No `[[ ]]`, no arrays in portable paths, no bash-only expansions in files sourced by both bash and zsh.

## Quick reference paths

- Installer: `run.sh`
- Main helper functions: `aliases:137-380` (tmux, aws-vault, terraform, node, local servers)
- Brewfiles: `darwin/Brewfile`, `linux/Brewfile`
- Arch zprofiles: `darwin/zprofile.{arm64,x86_64}.sh`, `linux/zprofile.{x86_64,aarch64,armv7l}.sh`
- Claude Code settings: `claude/settings.json`
- Korean ₩→` keymap: `darwin/DefaultkeyBinding.dict`

For architecture diagrams and installation flow sequence, see [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).
