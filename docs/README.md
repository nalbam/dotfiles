# Documentation

Choose a guide by the task you want to complete.

| Task | Start here |
|------|------------|
| Install a machine or run `dot` | [Quick Start](../README.md#quick-start), [dot commands](../README.md#dot-명령) |
| Check what a platform installs | [Platforms and modules](../README.md#플랫폼과-모듈) |
| Keep machine-specific values out of Git | [Machine settings](../README.md#머신별-설정) |
| Operate models or monitoring on DGX Spark | [DGX Spark stack](../stacks/dgx-spark/README.md) |
| Upload Grafana dashboards | [Grafana dashboards](../stacks/grafana/README.md) |
| Add a module or platform, or diagnose a run | [Architecture](ARCHITECTURE.md) |
| Edit, verify or deploy AI settings | [AI Tools Sync](../README.md#ai-tools-sync) |
| Choose development agents and coordinate their work | [Development Agents](DEVELOPMENT_AGENTS.md) |
| Choose a shared AI skill | [Skills](SKILLS.md) |
| Use the Neovim configuration | [Neovim](../config/nvim/README.md) |
| Change shell helpers | [aliases](../config/shell/aliases) |
| Work on this repository with an agent | [AGENTS.md](../AGENTS.md); `CLAUDE.md` links to the same file |

## Configuration sources

- Platforms: [profiles](../profiles); modules: [modules](../modules).
- Packages: [macOS Brewfile](../packages/Brewfile.darwin), [Linux Brewfile](../packages/Brewfile.linux).
- Shell startup: [Zsh](../config/shell/zshrc), [Bash](../config/shell/bashrc), [profile](../config/shell/profile), [nvm loader](../config/shell/nvm.sh) and [platform zprofiles](../config/shell/zprofile).
- Git identities: [base configuration](../config/git/gitconfig) and the `gitconfig-*` files next to it.
- Terminal and editor settings: [Ghostty](../config/terminal/ghostty.config), [iTerm2](../config/terminal/iterm2-profiles.json), [tmux](../config/tmux/tmux.conf), [Vim](../config/vim/vimrc).
- OS settings: [macOS preferences](../config/macos/defaults.sh).

## Documentation principles

Write for the reader's task. Apply ISO 24495-1 principles to make information easy to find, understand, and use, and ASD-STE100 principles to keep wording short, clear, and unambiguous. Preserve commands, identifiers, conditions, and technical meaning.

The shared [documentation workflow](../claude/skills/docs-sync/SKILL.md#작성-품질) defines the review checks. These checks support writing quality; they do not establish full compliance with either standard.
