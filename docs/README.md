# Documentation

Choose a guide by the task you want to complete.

| Task | Start here |
|------|------------|
| Install or rerun dotfiles | [Quick Start](../README.md#quick-start) |
| Understand installation order, backups, or failures | [Architecture](ARCHITECTURE.md) |
| Edit, verify, or deploy AI settings | [AI Tools Sync](../README.md#ai-tools-sync) |
| Choose a shared AI skill | [Skills](../claude/skills/README.md) |
| Prepare a fresh Ubuntu server as root | [Linux setup](../linux/README.md) |
| Install the separate Neovim configuration | [Neovim setup](../nvim/README.md) |
| Change shell helpers | [aliases](../aliases) |
| Work on this repository with an agent | [AGENTS.md](../AGENTS.md); `CLAUDE.md` links to the same file |

## Configuration sources

- Packages: [macOS Brewfile](../darwin/Brewfile), [Linux Brewfile](../linux/Brewfile).
- Shell startup: [Zsh](../zshrc), [Bash](../bashrc), [profile](../profile), and platform `zprofile.*.sh` files.
- Git identities: [base configuration](../gitconfig), [nalbam](../gitconfig-nalbam), [bruce](../gitconfig-bruce), [yujh404](../gitconfig-yujh404).
- Terminal and editor settings: [Ghostty](../ghostty/config), [iTerm2](../iterm2/profiles.json), [tmux](../tmux.conf), [Vim](../vimrc).
- OS settings: [macos](../macos). The installer does not automatically apply every configuration file in the repository.

## Documentation principles

Write for the reader's task. Apply ISO 24495-1 principles to make information easy to find, understand, and use, and ASD-STE100 principles to keep wording short, clear, and unambiguous. Preserve commands, identifiers, conditions, and technical meaning.

The shared [documentation workflow](../claude/skills/docs-sync/SKILL.md#작성-품질) defines the review checks. These checks support writing quality; they do not establish full compliance with either standard.
