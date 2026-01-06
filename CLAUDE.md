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

The installation follows a 10-step process:
1. System environment check (OS/architecture detection)
2. Directory setup and SSH key generation
3. Dotfiles repository cloning/updating
4. Basic configuration files setup (SSH, AWS, Git configs)
5. Package manager setup (APT for Linux, Homebrew installation)
6. Development packages installation (Homebrew, NPM, PIP)
7. OS-specific settings (macOS system preferences, Xcode)
8. ZSH and Oh-My-ZSH installation
9. Theme and UI settings (Dracula theme, iTerm2)
10. User configuration files deployment

## Key Components

- **`run.sh`**: Main installation script with 10-step progress tracking
- **`run.ps1`**: Windows PowerShell installation script
- **`darwin/Brewfile`**: macOS package definitions
- **`linux/Brewfile`**: Linux package definitions
- **`docs/`**: Technical documentation (ARCHITECTURE.md)
- **`claude/`**: Claude Code AI settings and instructions
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

## Platform-Specific Notes

### macOS (Darwin)
- **arm64**: Apple Silicon Macs, Homebrew at `/opt/homebrew`
- **x86_64**: Intel Macs, Homebrew at `/usr/local`
- Includes Xcode Command Line Tools installation
- iTerm2 Dracula theme integration
- System preferences automation via `.macos` script

### Linux
- **x86_64**: WSL (Windows Subsystem for Linux) or native Ubuntu/Debian
- **aarch64**: Raspberry Pi 64-bit OS
- **armv7l**: Raspberry Pi 32-bit OS
- Homebrew at `/home/linuxbrew/.linuxbrew` (optional)
- APT package manager with daily update throttling
- All zprofile files gracefully handle missing brew/pyenv

### WSL-Specific Considerations
- Detected as Linux with x86_64 architecture
- Homebrew installation is optional but supported
- Windows notifications available via notify.sh
- Network access inherits from Windows host

### Raspberry Pi Considerations
- ARM architecture (aarch64 or armv7l)
- May require `sudo` for npm global package installations
- Homebrew installation optional due to ARM compilation requirements
- Lower memory footprint - some heavy packages may be skipped
