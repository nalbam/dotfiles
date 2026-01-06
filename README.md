# dotfiles

Development environment automation tool that helps you quickly set up a consistent development environment across macOS, Linux, and Windows.

## Supported Environments

- macOS (darwin) - arm64/x86_64
- Linux - x86_64
- Windows (mingw64)

## Key Features

- Automated Git configuration with organization-specific settings
- Automatic SSH key generation (RSA, ED25519)
- AWS CLI configuration
- Homebrew/APT package management
- ZSH and Oh-My-ZSH installation
- Dracula theme integration
- iTerm2 configuration (macOS)
- Custom alias settings
- Claude Code AI settings

## Installation

### macOS / Linux

```bash
bash -c "$(curl -fsSL nalbam.github.io/dotfiles/run.sh)"
```

### Windows (PowerShell)

```powershell
./run.ps1
```

## Directory Structure

```
.
├── darwin/            # macOS specific settings
│   ├── Brewfile       # macOS Homebrew package list
│   └── .zprofile.*    # macOS architecture-specific profile settings
├── linux/             # Linux specific settings
│   ├── Brewfile       # Linux Homebrew package list
│   └── .zprofile.*    # Linux profile settings
├── claude/            # Claude Code AI settings
│   ├── CLAUDE.md      # Claude Code instructions (EN)
│   ├── CLAUDE.ko.md   # Claude Code instructions (KO)
│   └── settings.json  # Claude Code configuration
└── docs/              # Technical documentation
    └── ARCHITECTURE.md # System architecture
```

## Main Configuration Files

- `.gitconfig`: Git default settings
- `.zshrc`: ZSH shell configuration
- `.vimrc`: Vim editor settings
- `.aliases`: Custom command aliases
- `.profile`: Shell environment variables
- `.macos`: macOS system settings

## Automatically Installed Tools

### Via Homebrew

- Git, GitHub CLI (gh)
- AWS CLI, eksctl
- Kubernetes tools (kubectl, helm, argocd, k9s, kubectx)
- Terraform tools (tenv, terraform-docs)
- Development tools (jq, yq, fzf, ripgrep, curl, wget, etc.)
- Language tools (Go, Ruby, Python/pyenv, Node.js/nvm)
- ZSH and Oh-My-ZSH with plugins

### Via NPM

- Claude Code (@anthropic-ai/claude-code)
- ccusage (Claude Code usage tracker)
- Serverless Framework

### Via PIP

- toast-cli

## How to Contribute

1. Fork this repository
2. Create a new branch
3. Commit your changes
4. Push to your forked repository
5. Create a Pull Request

## License

This project is licensed under the MIT License.
