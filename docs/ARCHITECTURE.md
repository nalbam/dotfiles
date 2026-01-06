# Architecture

## Overview

This project is a development environment automation tool that provides consistent setup across different operating systems. It follows a modular architecture with clear separation of concerns.

## Core Components

```mermaid
graph TD
    A[run.sh] --> B[System Detection]
    A --> C[Configuration Management]
    A --> D[Package Management]
    A --> E[Shell Environment]

    B --> B1[OS Detection]
    B --> B2[Architecture Detection]

    C --> C1[Git Config]
    C --> C2[SSH Config]
    C --> C3[AWS Config]
    C --> C4[macOS Settings]

    D --> D1[Homebrew]
    D --> D2[APT]
    D --> D3[Chocolatey]

    E --> E1[ZSH]
    E --> E2[Oh My ZSH]
    E --> E3[Dracula Theme]
```

## Directory Structure

```
.
├── run.sh              # Main installation script (10-step process)
├── run.ps1             # Windows PowerShell installation script
├── darwin/             # macOS specific configurations
│   ├── Brewfile        # macOS Homebrew package list
│   └── .zprofile.*     # Architecture-specific profile settings
├── linux/              # Linux specific configurations
│   ├── Brewfile        # Linux Homebrew package list
│   └── .zprofile.*     # Profile settings
└── claude/             # Claude Code AI settings
    ├── CLAUDE.md       # Claude Code instructions (EN)
    ├── CLAUDE.ko.md    # Claude Code instructions (KO)
    └── settings.json   # Claude Code configuration
```

## Core Functions

1. System Detection
   - OS detection (darwin/linux/windows)
   - Architecture detection (x86_64/arm64)
   - Package manager selection (brew/apt/choco)

2. Configuration Management
   - Git configuration with organization-specific settings
   - SSH key generation and configuration
   - AWS CLI configuration
   - macOS system preferences

3. Package Management
   - Homebrew for macOS and Linux
   - APT for Linux
   - Chocolatey for Windows
   - NPM for Node.js packages (claude-code, ccusage, serverless)
   - PIP for Python packages (toast-cli)
   - Daily update optimization with timestamp tracking (12-hour interval)

4. Shell Environment
   - ZSH as default shell
   - Oh My ZSH installation
   - Dracula theme integration
   - Custom aliases and profiles

## Installation Flow

```mermaid
sequenceDiagram
    participant User
    participant Script
    participant System
    participant Network

    User->>Script: Execute run.sh
    Script->>System: Step 1: Detect OS & Architecture
    Script->>System: Step 2: Create directories & SSH keys
    Script->>Network: Step 3: Clone/Update dotfiles
    Note over Network: Retry mechanism with exponential backoff
    Script->>System: Step 4: Setup config files (SSH, AWS, Git)
    Script->>System: Step 5: Setup package managers
    Script->>Network: Step 6: Install packages (Homebrew, NPM, PIP)
    Script->>System: Step 7: OS-specific settings
    Script->>System: Step 8: Install ZSH & Oh My ZSH
    Script->>System: Step 9: Apply theme & UI settings
    Script->>System: Step 10: Deploy user config files
    Script->>User: Complete Installation
```

## Security Considerations

1. File Permissions
   - SSH config: 600
   - AWS config: 600
   - Backup files: 600
   - Automatic permission setting for sensitive files
   - Secure backup handling

2. Authentication
   - SSH key generation
   - Git credentials management
   - Organization-specific email configuration
   - Safe credential handling

## Performance Optimization

1. Package Management
   - Daily update limitation with timestamp tracking
   - Intelligent update scheduling
   - Optimized download retry mechanism
   - Connection timeout handling

2. Installation Process
   - Progress tracking with step counting
   - Modular installation steps
   - Conditional execution
   - Efficient error recovery

## Error Handling

1. System Compatibility
   - OS version verification
   - Architecture compatibility check
   - Package manager availability
   - Directory access verification

2. Network Issues
   - Exponential backoff retry mechanism
   - Connection timeout handling
   - Maximum retry attempts (3회)
   - Detailed error reporting
   - Graceful fallback handling

3. File Operations
   - Backup creation verification
   - Permission setting validation (600 for sensitive files)
   - File integrity checks using MD5
   - Safe directory navigation with error handling

## Future Considerations

1. Extensibility
   - Plugin system for custom configurations
   - Organization-specific extensions
   - Custom theme support
   - Enhanced error handling patterns

2. Maintenance
   - Version control
   - Dependency updates
   - Configuration backups
   - Automated testing integration
