# dotfiles

Development environment automation tool that helps you quickly set up a consistent development environment across macOS, Linux, and Windows.

## Supported Environments

- macOS (darwin)
- Linux
- Windows (mingw64)

## Key Features

- Automated Git configuration
- Automatic SSH key generation (RSA, ED25519)
- AWS CLI configuration
- Homebrew package management
- ZSH and Oh-My-ZSH installation
- Dracula theme integration
- iTerm2 configuration (macOS)
- Custom alias settings

## Installation

```bash
bash -c "$(curl -fsSL nalbam.github.io/dotfiles/run.sh)"
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
└── bin/               # Utility scripts
```

## Main Configuration Files

- `.gitconfig`: Git default settings
- `.zshrc`: ZSH shell configuration
- `.vimrc`: Vim editor settings
- `.aliases`: Custom command aliases
- `.profile`: Shell environment variables
- `.macos`: macOS system settings

## Automatically Installed Tools

- Git
- AWS CLI
- Kubernetes tools (kubectl, helm, argocd)
- Development tools (jq, curl, wget, etc.)
- ZSH and Oh-My-ZSH
- Dracula theme

## How to Contribute

1. Fork this repository
2. Create a new branch
3. Commit your changes
4. Push to your forked repository
5. Create a Pull Request

## License

This project is licensed under the MIT License.
