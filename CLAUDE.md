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
- **Configuration files**: `.gitconfig`, `.zshrc`, `.aliases`, `.vimrc`, `.bashrc`, `.profile`, etc.

## Claude Code Integration

The dotfiles include comprehensive Claude Code (AI pair programming CLI) setup:

### Directory Structure
- **`claude/CLAUDE.md`**: Project-specific Claude instructions
- **`claude/settings.json`**: Claude permissions, hooks, and status line configuration
- **`claude/hooks/notify.sh`**: Multi-platform notification system
- **`claude/agents/`**: Custom agent definitions
  - `code-reviewer.md`: Code review specialist
  - `debugger.md`: Debugging and error resolution
  - `test-writer.md`: Test generation specialist
  - `refactorer.md`: Code refactoring specialist
  - `doc-writer.md`: Documentation specialist
  - `validator.md`: **NEW** - Runs lint, typecheck, tests and fixes issues
- **`claude/sounds/`**: Audio notifications (ding1.mp3, ding2.mp3, ding3.mp3)
- **`claude/env.sample`**: Environment variables template

### Notification System
The `notify.sh` hook provides notifications when Claude completes tasks or needs input:
- **macOS**: Native system notifications + audio alerts (afplay)
- **WSL**: PowerShell beep notifications
- **ntfy.sh**: Cross-platform push notifications to mobile devices (set `NTFY_TOPIC`)
- **Slack**: Webhook-based notifications (set `SLACK_WEBHOOK_URL`)

### Status Line Integration
Uses `ccusage statusline` to display Claude Code usage statistics in the CLI

### Custom Agents
Custom agents provide specialized workflows:

**validator** - Comprehensive quality validation:
```bash
# Usage in Claude Code CLI
/validator

# Or ask Claude naturally
"Run validator to check my code"
```

The validator agent:
1. Detects project type (Node.js, Python, Go, Ruby, Java, Rust)
2. Runs lint checks (eslint, pylint, rubocop, etc.)
3. Runs type checks (tsc, mypy, flow, etc.)
4. Runs test suite (jest, pytest, go test, etc.)
5. Analyzes failures and identifies root causes
6. Fixes all issues automatically
7. Re-validates to ensure all checks pass

Perfect for pre-commit validation or CI/CD pipeline simulation.

### Permission Management
Pre-configured allow/deny lists for safe AI operations:
- Allows standard development tools (git, npm, docker, kubectl, etc.)
- Denies destructive operations (rm -rf /, shutdown, etc.)
- Protects sensitive files (.env, secrets, credentials)

## Organization-Specific Features

The installer detects organization context from hostname:
- `nalbam-*` hostnames: Uses `me@nalbam.com` email default
- `Karrot-*` or `daangn-*` hostnames: Uses `@daangn.com` email default
- Other hostnames: Uses `@gmail.com` email default

## Installed Packages

### NPM Packages
- **npm**: Package manager itself (auto-update)
- **corepack**: Node.js package manager manager
- **serverless**: Serverless framework CLI
- **@anthropic-ai/claude-code**: Claude Code AI assistant
- **ccusage**: Claude Code usage tracking and status line

### PIP Packages
- **toast-cli**: Toast notification utility
- Intelligent installation with fallback strategies:
  1. Normal pip install
  2. User install (--user)
  3. PEP 668 compliant (--break-system-packages --user)
  4. System-wide with sudo (last resort)

### Homebrew Packages (macOS & Linux)
Key tools include:
- **Cloud/DevOps**: awscli, eksctl, terraform, helm, kubectl, argocd, k9s
- **Development**: git, gh, hub, go, ruby, nvm, pyenv, direnv
- **Utilities**: jq, yq, fzf, ripgrep, tree, htop, httpie, curl, wget
- **Shell**: zsh, zsh-autosuggestions, zsh-syntax-highlighting

### macOS Casks
- **Essential**: 1password-cli, aws-vault-binary, iterm2, visual-studio-code
- **Fonts**: font-dejavu-sans-mono-nerd-font
- **User-specific** (if USER=nalbam): 1password, google-chrome, slack, zoom
- **Third-party taps**: opspresso/tap/toast, pakerwreah/calendr/calendr

## Error Handling & Resilience

- Network operations use exponential backoff (3 retries max with increasing wait times: 5s, 10s, 20s)
- File permissions automatically set for sensitive files (600 for .ssh/*, .aws/*, *.backup)
- Backup creation before overwriting existing configurations
- Update throttling for package managers (12 hours minimum between updates)
- MD5 integrity checks for file operations
- Automatic sudo detection and fallback for restricted operations
- Graceful degradation when optional tools are unavailable

## Security Features

- Automatic SSH key generation (RSA and ED25519)
- Secure file permissions (600) for SSH/AWS configs
- Safe backup handling with permission preservation
- Credential handling without exposure
- 1Password CLI integration for secure credential management

### 1Password Integration
The installer provides templates and instructions for using 1Password CLI:

```bash
# SSH config from 1Password
op read op://keys/ssh-config/notesPlain > ~/.ssh/config && chmod 600 ~/.ssh/config

# SSH private keys from 1Password
op read op://keys/nalbam-seoul.pem/notesPlain > ~/.ssh/nalbam-seoul.pem && chmod 600 ~/.ssh/nalbam-seoul.pem

# AWS credentials from 1Password
op read op://keys/aws-config/notesPlain > ~/.aws/config && chmod 600 ~/.aws/config
op read op://keys/aws-credentials/notesPlain > ~/.aws/credentials && chmod 600 ~/.aws/credentials
```

This allows secure storage of credentials in 1Password vaults instead of plain text files.

## Development Notes

- Uses POSIX-compliant shell scripting
- Progress tracking with colored output using `tput`
- Modular function design for maintainability
- Cross-platform compatibility (Darwin/Linux/MinGW64)

## Platform-Specific Notes

### macOS (Darwin)
- **arm64**: Apple Silicon Macs, Homebrew at `/opt/homebrew`
  - Automatic Rosetta 2 installation for x86_64 compatibility
- **x86_64**: Intel Macs, Homebrew at `/usr/local`
- Includes Xcode Command Line Tools installation
- iTerm2 Dracula theme integration with profiles.json
- System preferences automation via `.macos` script
- Korean keyboard won symbol (₩) mapped to backtick (`) via `DefaultkeyBinding.dict`
- GNU getopt linking for compatibility

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

## Advanced Features

### Version-Aware Package Management
- NPM and PIP packages check installed vs. latest versions before updating
- Skip updates if already at latest version to save time
- Display version changes in update messages (e.g., "Updating npm: 8.1.0 → 10.2.3")

### Intelligent Permission Handling
- Automatic detection of write permissions for npm global installs
- Fallback chain for PIP installs (normal → --user → --break-system-packages → sudo)
- Smart sudo usage only when necessary

### Update Throttling
- Timestamp-based tracking prevents excessive package manager updates
- APT and Homebrew updates limited to once per 12 hours
- Timestamp files: `~/.apt_last_update`, `~/.brew_last_update`

### Git Configuration Variants
Multiple gitconfig profiles for different contexts:
- `.gitconfig`: Base configuration
- `.gitconfig-nalbam`: Personal profile
- `.gitconfig-bruce`: Alternative profile
- Can be switched or merged based on project needs

### Shell Configuration
- Platform and architecture-specific `.zprofile` files:
  - `darwin/zprofile.arm64.sh`, `darwin/zprofile.x86_64.sh`
  - `linux/zprofile.x86_64.sh`, `linux/zprofile.aarch64.sh`, `linux/zprofile.armv7l.sh`
- Graceful handling of missing tools (brew, pyenv) in profile scripts
