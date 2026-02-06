# dotfiles

Development environment automation tool that helps you quickly set up a consistent development environment across macOS, Linux, and Windows.

## Supported Environments

- **macOS (darwin)** - arm64 (Apple Silicon), x86_64 (Intel)
- **Linux** - x86_64 (WSL/Ubuntu), aarch64 (Raspberry Pi 64-bit), armv7l (Raspberry Pi 32-bit)
- **Windows** (mingw64)

## Key Features

- Automated Git configuration with organization-specific settings
- Automatic SSH key generation (RSA, ED25519)
- AWS CLI configuration
- Homebrew/APT package management
- ZSH and Oh-My-ZSH installation
- Dracula theme integration
- iTerm2 configuration (macOS)
- Custom alias settings
- **Claude Code environment sync** - Maintain consistent Claude Code settings across all development machines

## Installation

### macOS / Linux

```bash
curl -fsSL nalbam.github.io/dotfiles/run.sh | bash
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
│   └── zprofile.*     # macOS architecture-specific profile settings
├── docs/              # Technical documentation
│   ├── README.md      # Documentation index
│   └── ARCHITECTURE.md # System architecture
└── linux/             # Linux specific settings
    ├── Brewfile       # Linux Homebrew package list
    └── zprofile.*     # Linux profile settings
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

- Git, GitHub CLI (gh), hub, git-lfs, git-secrets
- AWS CLI, eksctl
- Kubernetes tools (kubectl, helm, argo, argocd, istioctl, k9s, kubectx, kube-ps1)
- Terraform tools (tenv, terraform-docs, tfenv)
- Development tools (jq, yq, fzf, ripgrep, curl, wget, htop, httpie, grpcurl, graphviz, colordiff, figlet, fx, telnet, xz)
- Language tools (Go, Ruby, Python/pyenv/pipenv, Node.js/nvm)
- Security tools (gpg)
- ZSH and Oh-My-ZSH with plugins (zsh-autosuggestions, zsh-syntax-highlighting)

### macOS Casks

- 1password-cli, aws-vault-binary
- iterm2, visual-studio-code
- google-drive
- font-dejavu-sans-mono-nerd-font

### Via NPM

- ccusage (Claude Code usage tracker)
- Serverless Framework
- corepack (Node.js package manager manager)

### Via PIP

- toast-cli (workspace and environment management tool)

## Custom Aliases

The `.aliases` file provides many useful shortcuts:

- **Toast CLI**: `t` (toast), `tu` (toast-cli update), `c` (change directory), `m` (caller-identity), `x` (context), `d` (dot), `e` (env), `g` (git), `r` (region), `p` (prompt), `ssm` (SSM), `tt` (dotfiles reinstall), `vv` (vibe-config sync)
- **AWS**: `a` (aws), `av` (aws-vault helper with profile shortcuts: alpha, data, prod, nalbam, etc.)
- **Kubernetes**: `k` (kubectl), `h` (helm)
- **Terraform**: `tf`, `tfp` (plan), `tfa` (apply), `tfd` (destroy), `tfs` (state), `tfo` (output), `tfdoc` (docs)
- **Node.js**: `nn` (clean install with pnpm/npm detection), `nb` (build), `nd` (dev server), `nk` (kill dev servers on ports 3000-3999)
- **Local Servers**: `ss` (start HTTP server), `sl` (list all servers), `sk` (kill by port or all)
- **Claude**: `cc` (claude), `ccc` (--continue), `ccd` (claude doctor), `ccu` (ccusage)
- **Python**: `py`, `py3`, `pip` (pip3), `pipi` (install), `pipu` (upgrade), `pipr` (requirements), `pipf` (freeze), `pipl` (list)
- **Utilities**: `dt` (UTC timestamp), `dff` (colordiff), `ll` (ls -l), `l` (ls -al)
- **Serverless**: `slsd` (sls deploy), `amp` (amplify)
- **SSM**: `sg` (ssm get), `sp` (ssm put)
- **Korean**: `ㅊ` (c), `ㅊㅇ` (cd), `ㅅㅅ` (tt), `ㅍㅍ` (vv)

## How to Contribute

1. Fork this repository
2. Create a new branch
3. Commit your changes
4. Push to your forked repository
5. Create a Pull Request

## License

This project is licensed under the MIT License.
