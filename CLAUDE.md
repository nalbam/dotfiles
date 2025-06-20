# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a dotfiles repository that provides automated development environment setup across macOS, Linux, and Windows platforms. It's a shell-based automation tool that configures Git, SSH, package managers, shell environments, and development tools.

## Main Installation Commands

```bash
# Primary installation method (run from anywhere)
bash -c "$(curl -fsSL nalbam.github.io/dotfiles/run.sh)"

# Local installation (if repository is already cloned)
./run.sh

# Windows installation
./run.ps1
```

## Architecture

The installation follows a multi-step process:
1. System detection (OS/architecture)
2. Directory setup and SSH key generation
3. Dotfiles repository cloning/updating
4. Git configuration (interactive)
5. OS-specific package manager setup
6. Homebrew/APT package installation
7. ZSH and Oh-My-ZSH installation
8. Dracula theme setup
9. Configuration file deployment

## Key Components

- **`run.sh`**: Main installation script with 8-step progress tracking
- **`run.ps1`**: Windows PowerShell installation script
- **`darwin/Brewfile`**: macOS package definitions
- **`linux/Brewfile`**: Linux package definitions
- **Configuration files**: `.gitconfig`, `.zshrc`, `.aliases`, `.vimrc`, etc.

## Organization-Specific Features

The installer detects organization context from hostname:
- `nalbam-*` hostnames: Uses `me@nalbam.com` email default
- `Karrot-*` or `daangn-*` hostnames: Uses `@daangn.com` email default
- Other hostnames: Uses `@gmail.com` email default

## Error Handling & Resilience

- Network operations use exponential backoff (3 retries max)
- File permissions automatically set for sensitive files (600)
- Backup creation before overwriting existing configurations
- Daily update throttling for package managers
- MD5 integrity checks for file operations

## Security Features

- Automatic SSH key generation (RSA and ED25519)
- Secure file permissions (600) for SSH/AWS configs
- Safe backup handling with permission preservation
- Credential handling without exposure

## Development Notes

- Uses POSIX-compliant shell scripting
- Progress tracking with colored output using `tput`
- Modular function design for maintainability
- Cross-platform compatibility (Darwin/Linux/MinGW64)
