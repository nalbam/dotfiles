# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a dotfiles repository that provides automated development environment setup across macOS, Linux, and Windows platforms. It's a shell-based automation tool that configures Git, SSH, package managers, shell environments, and development tools.

## Main Installation Commands

```bash
# Primary installation method (run from anywhere)
curl -fsSL nalbam.github.io/dotfiles/run.sh | bash

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
- **Configuration files**: `.gitconfig`, `.zshrc`, `.aliases`, `.vimrc`, `.bashrc`, `.profile`, etc.

## Claude Code Integration

Claude Code settings are managed in a separate repository: [vibe-config](https://github.com/nalbam/vibe-config)

To sync Claude Code settings:
```bash
bash -c "$(curl -fsSL nalbam.github.io/vibe-config/sync.sh)"
```

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
- **ccusage**: Claude Code usage tracking and status line

### PIP Packages
- **toast-cli**: Workspace and environment management tool (integrated extensively in shell aliases)
- Intelligent installation with fallback strategies:
  1. Normal pip install
  2. User install (--user)
  3. PEP 668 compliant (--break-system-packages --user)
  4. System-wide with sudo (last resort)

### Homebrew Packages (macOS & Linux)
Key tools include:
- **Cloud/DevOps**: awscli, eksctl, tenv, helm, kubectl, argo, argocd, k9s, kubectx, kube-ps1, istioctl (macOS only)
- **Development**: git, gh, hub, git-lfs, git-secrets, go, ruby, nvm, pyenv, direnv, pipenv (macOS only)
- **Utilities**: jq, yq, fzf, tree, httpie, curl, wget, grpcurl, colordiff, figlet, fx, xz, ripgrep/htop/telnet/graphviz (macOS only)
- **Security**: gpg, 1password-cli
- **Shell**: zsh, zsh-autosuggestions, zsh-syntax-highlighting

### macOS Casks
- **Essential**: 1password-cli, aws-vault-binary, iterm2, visual-studio-code, google-drive
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

### Toast CLI Integration
The dotfiles provide extensive integration with Toast CLI for workspace management:
- **Directory Navigation**: `c()` function for workspace-aware directory changes
- **Context Management**: Quick shortcuts for AWS (`m`), Kubernetes (`x`), Git (`g`), regions (`r`)
- **Environment Helpers**: `e` (env), `d` (dot), `p` (prompt), `ssm` (SSM parameters)
- **Installation**: Auto-installed via PIP, auto-updated with `tu` alias
- **Quick Reinstall**: `tt` alias to re-run dotfiles installer

### Development Helper Functions
Beyond simple aliases, the repository includes intelligent helper functions:

**Node.js Ecosystem** (in `aliases:116-158`):
- `nn()`: Smart clean install with automatic pnpm/npm detection
- `nb()`: Smart build command (pnpm/npm auto-detection)
- `nd()`: Start dev server with automatic port cleanup
- `nk()`: Kill dev servers on ports 3000-3999

**Local Server Management** (in `aliases:176-243`):
- `ss([dir], [port])`: Start Python HTTP server (default: docs/, port 8000)
- `sl()`: List all running local dev servers
- `sk(<port|all>)`: Kill servers by port or all at once

**AWS Vault Helper** (in `aliases:39-79`):
- `av()`: Profile-aware AWS Vault execution with shortcuts
  - Profiles: `a|alpha`, `d|data`, `p|prod`, `n|nalbam`, `t|two`, `k|krug`, `o|ops`, `b|bruce`
  - Commands: `c|clear`, `l|list`
  - Example: `av n kubectl get pods` (execute kubectl in nalbam profile)

**Terraform Workflows** (in `aliases:84-107`):
- Complete set of aliases for init, plan, apply, destroy
- State management shortcuts (`tfsl`, `tfss`, `tfsr`)
- Auto-formatting and validation (`tff`, `tfp`)

### Tool Version Managers
Integrated version managers with automatic configuration:
- **tfenv**: Terraform version manager with `TFENV_AUTO_INSTALL=true` and ARM64 support
- **pyenv**: Python version manager with automatic initialization
- **nvm**: Node.js version manager with automatic loading

### Terminal Integration
- **VS Code**: Shell integration for VS Code terminal (auto-detected)
- **Kiro**: Shell integration for Kiro terminal (auto-detected)
- **Kubernetes**: `kube-ps1` prompt integration showing current cluster/namespace

### Korean Keyboard Support
Native Korean character aliases for quick command execution:
- `ㅊ` → `c` (change directory with toast)
- `ㅊㅇ` → `cd` (change directory)
- `ㅅㅅ` → `tt` (re-run dotfiles installer)
- `ㅍㅍ` → `vv` (sync vibe-config)
