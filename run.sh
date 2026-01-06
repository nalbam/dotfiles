#!/bin/bash

################################################################################
# 선언 영역 (Declaration Section)
################################################################################

# OS 정보 및 설치 도구 설정
OS_NAME="$(uname | awk '{print tolower($0)}' | cut -d'-' -f1)"
OS_ARCH="$(uname -m)"

if [ "${OS_NAME}" == "darwin" ]; then
  INSTALLER="brew"
elif [ "${OS_NAME}" == "linux" ]; then
  INSTALLER="apt"
elif [ "${OS_NAME}" == "mingw64_nt" ]; then
  INSTALLER="choco"
fi

# 설치 진행 단계 설정
TOTAL_STEPS=10
CURRENT_STEP=0

# 타이머 설정
UPDATE_INTERVAL=43200  # 12시간 (초 단위)

# 컬러 출력 설정
command -v tput >/dev/null && TPUT=true

################################################################################
# 함수 영역 (Function Section)
################################################################################

# 컬러 출력 함수
_echo() {
  if [ "${TPUT}" != "" ] && [ "$2" != "" ]; then
    echo -e "$(tput setaf $2)$1$(tput sgr0)"
  else
    echo -e "$1"
  fi
}

# 시작 배너 출력 함수
_banner() {
  _echo
  _echo "╔════════════════════════════════════════════════════════════════╗" 6
  _echo "║                       DOTFILES INSTALLER                       ║" 6
  _echo "║          Development Environment Setup Automation Tool         ║" 6
  _echo "╚════════════════════════════════════════════════════════════════╝" 6
}

# 진행률 표시 함수
_progress() {
  CURRENT_STEP=$((CURRENT_STEP + 1))
  _echo "\n▶ [$CURRENT_STEP/$TOTAL_STEPS] $@" 6
}

# 정보 메시지 출력 함수 (파랑)
_info() {
  _echo "  ℹ $@" 4
}

# 성공 메시지 출력 함수 (초록)
_ok() {
  _echo "  ✓ $@" 2
}

# 건너뛰기 메시지 출력 함수 (노랑)
_skip() {
  _echo "  ⊘ $@" 3
}

# 경고 메시지 출력 함수 (노랑)
_warn() {
  _echo "  ⚠ $@" 3
}

# 명령어 실행 표시 함수 (마젠타)
_run() {
  _echo "  → $@" 5
}

# 에러 메시지 출력 함수 (빨강)
_error() {
  _echo "\n✗ ERROR: $@\n" 1
  exit 1
}

# 최종 성공 메시지 출력 함수 (초록)
_success() {
  _echo
  _echo "╔════════════════════════════════════════════════════════════════╗" 2
  _echo "║                    INSTALLATION COMPLETED!                     ║" 2
  _echo "╚════════════════════════════════════════════════════════════════╝" 2
  _echo
  exit 0
}

# 레거시 함수 (하위 호환성 유지)
_result() {
  _info "$@"
}

_command() {
  _run "$@"
}

# MD5 해시 함수 (크로스 플랫폼)
_md5() {
  if [ "${OS_NAME}" == "darwin" ]; then
    md5 -q "$1"
  else
    md5sum "$1" | awk '{print $1}'
  fi
}

# 백업 생성 함수
_backup() {
  if [ -f "$1" ]; then
    if ! cp "$1" "$1.backup"; then
      _error "Failed to create backup of $1"
    fi
    # Set secure permissions for backup files
    chmod 600 "$1.backup"
    _result "Created backup: $1.backup"
  fi
}

# 파일 다운로드 함수
_download() {
  local max_retries=3
  local retry_count=0
  local wait_time=5

  # 대상 파일의 디렉토리 자동 생성
  local target_file=~/$1
  local target_dir=$(dirname "$target_file")
  if [ "$target_dir" != "$HOME" ] && [ ! -d "$target_dir" ]; then
    mkdir -p "$target_dir"
  fi

  if [ -f ~/.dotfiles/${2:-$1} ]; then
    if [ -f ~/$1 ]; then
      if [ "$(_md5 ~/.dotfiles/${2:-$1})" != "$(_md5 ~/$1)" ]; then
        _backup ~/$1
        cp ~/.dotfiles/${2:-$1} ~/$1
      fi
    else
      cp ~/.dotfiles/${2:-$1} ~/$1
    fi
  else
    _backup ~/$1
    while [ $retry_count -lt $max_retries ]; do
      if curl -fsSL --connect-timeout 10 -o ~/$1 https://raw.githubusercontent.com/nalbam/dotfiles/main/${2:-$1}; then
        break
      else
        retry_count=$((retry_count + 1))
        if [ $retry_count -eq $max_retries ]; then
          _error "Failed to download ${2:-$1} after $max_retries attempts"
        fi
        _echo "Download failed, retrying in $wait_time seconds..." 3
        sleep $wait_time
        wait_time=$((wait_time * 2))
      fi
    done
  fi

  # Set appropriate permissions for sensitive files
  case "$1" in
    .ssh/* | .aws/* | *.backup)
      chmod 600 ~/$1
      ;;
  esac
}

# Dotfiles 저장소 관리 함수
_dotfiles() {
  command -v git >/dev/null || HAS_GIT=false
  if [ -z "${HAS_GIT}" ]; then
    local max_retries=3
    local retry_count=0
    local wait_time=5

    if [ ! -d ~/.dotfiles ]; then
      _run "Cloning dotfiles repository..."
      while [ $retry_count -lt $max_retries ]; do
        if git clone https://github.com/nalbam/dotfiles.git ~/.dotfiles 2>/dev/null; then
          _ok "Dotfiles repository cloned"
          break
        else
          retry_count=$((retry_count + 1))
          if [ $retry_count -eq $max_retries ]; then
            _error "Failed to clone dotfiles repository after $max_retries attempts"
          fi
          _warn "Clone failed, retrying in $wait_time seconds... (attempt $retry_count/$max_retries)"
          sleep $wait_time
          wait_time=$((wait_time * 2))
        fi
      done
    else
      cd ~/.dotfiles || _error "Failed to change directory to ~/.dotfiles"
      _run "Updating dotfiles repository..."
      retry_count=0
      wait_time=5
      while [ $retry_count -lt $max_retries ]; do
        if git pull 2>/dev/null; then
          _ok "Dotfiles repository updated"
          break
        else
          retry_count=$((retry_count + 1))
          if [ $retry_count -eq $max_retries ]; then
            cd - >/dev/null || _error "Failed to return to previous directory"
            _error "Failed to update dotfiles repository after $max_retries attempts"
          fi
          _warn "Pull failed, retrying in $wait_time seconds... (attempt $retry_count/$max_retries)"
          sleep $wait_time
          wait_time=$((wait_time * 2))
        fi
      done
      cd - >/dev/null || _error "Failed to return to previous directory"
    fi
  fi
}

# NPM 패키지 설치 함수 (버전 체크 포함)
_install_npm_package() {
  local package_name="$1"
  local package_spec="$2"

  # npm 전역 경로의 쓰기 권한 체크
  local npm_prefix=$(npm config get prefix 2>/dev/null || echo "/usr/local")
  local needs_sudo=false

  if [ ! -w "$npm_prefix" ] || [ ! -w "$npm_prefix/lib" ] || [ ! -w "$npm_prefix/lib/node_modules" ] 2>/dev/null; then
    needs_sudo=true
  fi

  local npm_cmd="npm"
  if [ "$needs_sudo" = true ]; then
    npm_cmd="sudo npm"
  fi

  # Check if package is installed
  if npm list -g "$package_spec" >/dev/null 2>&1; then
    local installed_version=$(npm list -g "$package_spec" --depth=0 2>/dev/null | grep "$package_name" | sed 's/.*@\([0-9.]*\).*/\1/')
    local latest_version=$(npm view "$package_spec" version 2>/dev/null)

    if [ -n "$installed_version" ] && [ -n "$latest_version" ]; then
      if [ "$installed_version" != "$latest_version" ]; then
        _run "Updating $package_name: $installed_version → $latest_version"
        $npm_cmd update -g "$package_spec" >/dev/null 2>&1
        _ok "$package_name updated to $latest_version"
      else
        _skip "$package_name already up to date ($installed_version)"
      fi
    else
      _run "Installing $package_name..."
      $npm_cmd install -g "$package_spec" >/dev/null 2>&1
      _ok "$package_name installed"
    fi
  else
    _run "Installing $package_name..."
    $npm_cmd install -g "$package_spec" >/dev/null 2>&1
    _ok "$package_name installed"
  fi
}

# PIP 패키지 설치 함수 (버전 체크 포함)
_install_pip_package() {
  local package_name="$1"

  # Python3 체크
  if ! command -v python3 >/dev/null 2>&1; then
    _skip "Python3 not found, skipping $package_name"
    return 1
  fi

  # pip 설치 권한 체크
  local needs_sudo=false
  local pip_install_opts=""

  # 시스템 site-packages 경로 확인
  local site_packages=$(python3 -c "import site; print(site.getsitepackages()[0])" 2>/dev/null)

  # site-packages 경로에 쓰기 권한이 없으면 권한 필요
  if [ -n "$site_packages" ] && [ -d "$site_packages" ]; then
    if [ ! -w "$site_packages" ]; then
      needs_sudo=true
    fi
  else
    # site-packages 경로를 확인할 수 없으면 --user 플래그 사용
    pip_install_opts="--user"
  fi

  local pip_cmd="python3 -m pip"
  if [ "$needs_sudo" = true ]; then
    pip_cmd="sudo python3 -m pip"
  fi

  # Check if package is installed
  if python3 -m pip show "$package_name" >/dev/null 2>&1; then
    local installed_version=$(python3 -m pip show "$package_name" 2>/dev/null | grep "Version:" | awk '{print $2}')
    local latest_version=$(python3 -m pip index versions "$package_name" 2>/dev/null | grep "LATEST:" | awk '{print $2}')

    if [ -n "$installed_version" ] && [ -n "$latest_version" ]; then
      if [ "$installed_version" != "$latest_version" ]; then
        _run "Updating $package_name: $installed_version → $latest_version"
        local install_error=$(mktemp)
        if $pip_cmd install --upgrade $pip_install_opts "$package_name" 2>"$install_error" >/dev/null; then
          _ok "$package_name updated to $latest_version"
          rm -f "$install_error"
        else
          _warn "$package_name update failed, trying with --user flag..."
          if python3 -m pip install --user --upgrade "$package_name" 2>"$install_error" >/dev/null; then
            _ok "$package_name updated to $latest_version (user install)"
            rm -f "$install_error"
          else
            _warn "Failed to update $package_name"
            if [ -s "$install_error" ]; then
              _warn "Error: $(tail -3 "$install_error" | head -1)"
            fi
            rm -f "$install_error"
          fi
        fi
      else
        _skip "$package_name already up to date ($installed_version)"
      fi
    else
      _run "Installing $package_name..."
      local install_error=$(mktemp)
      if $pip_cmd install $pip_install_opts "$package_name" 2>"$install_error" >/dev/null; then
        _ok "$package_name installed"
        rm -f "$install_error"
      else
        _warn "$package_name install failed, trying with --user flag..."
        if python3 -m pip install --user "$package_name" 2>"$install_error" >/dev/null; then
          _ok "$package_name installed (user install)"
          rm -f "$install_error"
        else
          _warn "Failed to install $package_name"
          if [ -s "$install_error" ]; then
            _warn "Error: $(tail -3 "$install_error" | head -1)"
          fi
          rm -f "$install_error"
        fi
      fi
    fi
  else
    _run "Installing $package_name..."
    local install_error=$(mktemp)
    if $pip_cmd install $pip_install_opts "$package_name" 2>"$install_error" >/dev/null; then
      # 설치 확인
      if python3 -m pip show "$package_name" >/dev/null 2>&1; then
        local new_version=$(python3 -m pip show "$package_name" 2>/dev/null | grep "Version:" | awk '{print $2}')
        _ok "$package_name installed (v$new_version)"
      else
        _ok "$package_name installed"
      fi
      rm -f "$install_error"
    else
      _warn "$package_name install failed, trying with --user flag..."
      if python3 -m pip install --user "$package_name" 2>"$install_error" >/dev/null; then
        if python3 -m pip show "$package_name" >/dev/null 2>&1; then
          local new_version=$(python3 -m pip show "$package_name" 2>/dev/null | grep "Version:" | awk '{print $2}')
          _ok "$package_name installed (v$new_version, user install)"
        else
          _ok "$package_name installed (user install)"
        fi
        rm -f "$install_error"
      else
        _warn "Failed to install $package_name"
        if [ -s "$install_error" ]; then
          _warn "Error: $(tail -3 "$install_error" | head -1)"
        fi
        rm -f "$install_error"
      fi
    fi
  fi
}

# APT 업데이트 체크 함수
should_run_apt_update() {
  if [ ! -f "$APT_TIMESTAMP_FILE" ]; then
    return 0
  fi

  current_time=$(date +%s)
  last_update=$(cat "$APT_TIMESTAMP_FILE")
  time_diff=$((current_time - last_update))

  if [ $time_diff -ge $UPDATE_INTERVAL ]; then
    return 0
  else
    return 1
  fi
}

# Homebrew 업데이트 체크 함수
should_run_brew_update() {
  if [ ! -f "$BREW_TIMESTAMP_FILE" ]; then
    return 0
  fi

  current_time=$(date +%s)
  last_update=$(cat "$BREW_TIMESTAMP_FILE")
  time_diff=$((current_time - last_update))

  if [ $time_diff -ge $UPDATE_INTERVAL ]; then
    return 0
  else
    return 1
  fi
}

################################################################################
# 실행 영역 (Execution Section)
################################################################################

# 시작 배너 출력
_banner

# Step 1: 시스템 환경 확인
_progress "Checking system environment..."
_info "Operating System: ${OS_NAME}"
_info "Architecture: ${OS_ARCH}"
_info "Package Manager: ${INSTALLER}"

if [ "${INSTALLER}" == "" ]; then
  _error "Unsupported operating system."
fi

# Step 2: 디렉토리 생성 및 SSH 키 설정
_progress "Creating directories and setting up SSH keys..."

mkdir -p ~/.aws
mkdir -p ~/.ssh
_ok "Directories created"

# Generate SSH keys
if [ ! -f ~/.ssh/id_rsa ]; then
  ssh-keygen -q -f ~/.ssh/id_rsa -N ''
  _ok "Generated RSA SSH key (~/.ssh/id_rsa)"
else
  _skip "RSA SSH key already exists"
fi

if [ ! -f ~/.ssh/id_ed25519 ]; then
  ssh-keygen -q -t ed25519 -f ~/.ssh/id_ed25519 -N ''
  _ok "Generated ED25519 SSH key (~/.ssh/id_ed25519)"
else
  _skip "ED25519 SSH key already exists"
fi

# Step 3: Dotfiles 저장소 클론
_progress "Cloning dotfiles repository..."
_dotfiles

# Step 4: 기본 설정 파일 다운로드
_progress "Setting up basic configuration files..."

# SSH 설정 파일 다운로드
if [ ! -f ~/.ssh/config ]; then
  _download .ssh/config ssh/config
  _ok "Downloaded SSH config template"
  _warn "To use 1Password: op read op://keys/ssh-config/notesPlain > ~/.ssh/config && chmod 600 ~/.ssh/config"
else
  _skip "SSH config already exists"
fi

# AWS 설정 파일 다운로드
if [ ! -f ~/.aws/config ]; then
  _download .aws/config aws/config
  _ok "Downloaded AWS config template"
  _warn "To use 1Password for AWS:"
  _warn "  op read op://keys/aws-config/notesPlain > ~/.aws/config && chmod 600 ~/.aws/config"
  _warn "  op read op://keys/aws-credentials/notesPlain > ~/.aws/credentials && chmod 600 ~/.aws/credentials"
else
  _skip "AWS config already exists"
fi

# Git 설정 파일 다운로드
_download .gitconfig gitconfig
_download .gitconfig-bruce gitconfig-bruce
_download .gitconfig-nalbam gitconfig-nalbam
_ok "Git configuration files downloaded"

# Step 5: OS별 패키지 관리자 설정
_progress "Setting up package managers..."

# Linux 설정 (APT 패키지 관리)
if [ "${OS_NAME}" == "linux" ]; then
  APT_TIMESTAMP_FILE=~/.apt_last_update

  if should_run_apt_update; then
    _run "Updating APT packages..."
    sudo apt update
    sudo apt upgrade -y
    _ok "APT packages updated"

    # Update timestamp
    date +%s > "$APT_TIMESTAMP_FILE"
  else
    _skip "APT update (last update was less than 12 hours ago)"
  fi

  # 기본 패키지 설치 (없는 경우에만)
  if ! command -v zsh >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
    _run "Installing essential packages (build-essential, git, zsh, jq, etc.)..."
    sudo apt install -y build-essential procps curl file git unzip jq zsh
    _ok "Essential packages installed"
  else
    _skip "Essential packages already installed"
  fi
fi

# Homebrew 설치
command -v brew >/dev/null || HAS_BREW=false
if [ ! -z "${HAS_BREW}" ]; then
  _run "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [ -d /opt/homebrew/bin ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -d /home/linuxbrew/.linuxbrew ]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
  else
    eval "$(brew shellenv)"
  fi
  _ok "Homebrew installed"
else
  _skip "Homebrew already installed"
fi

# Step 6: 개발 도구 패키지 설치
_progress "Installing development packages..."

# Homebrew 패키지 업데이트 (brew가 설치된 경우에만)
if command -v brew >/dev/null 2>&1; then
  BREW_TIMESTAMP_FILE=~/.brew_last_update

  if should_run_brew_update; then
    _run "Updating Homebrew packages..."
    brew update
    brew upgrade
    _ok "Homebrew packages updated"

    # Brewfile 기반 패키지 설치
    if [ -f ~/.dotfiles/$OS_NAME/Brewfile ]; then
      _download .Brewfile $OS_NAME/Brewfile
      _run "Installing packages from Brewfile..."
      brew bundle --file=~/.Brewfile
      brew cleanup
      _ok "Brewfile packages installed"
    else
      _skip "Brewfile not found for $OS_NAME"
    fi

    # Update timestamp
    date +%s > "$BREW_TIMESTAMP_FILE"
  else
    _skip "Homebrew update (last update was less than 12 hours ago)"
  fi

  # macOS getopt 설정
  if [ "${OS_NAME}" == "darwin" ]; then
    GETOPT=$(getopt 2>&1 | head -1 | xargs)
    if [ "${GETOPT}" == "--" ]; then
      brew link --force gnu-getopt
    fi
  fi
else
  _skip "Homebrew not found"
fi

# NPM 패키지 설치 (버전 체크 포함)
if command -v npm >/dev/null; then
  _info "Installing/updating NPM packages..."
  _install_npm_package "npm" "npm"
  _install_npm_package "corepack" "corepack"
  _install_npm_package "serverless" "serverless"
  _install_npm_package "claude-code" "@anthropic-ai/claude-code"
  _install_npm_package "ccusage" "ccusage"
else
  _skip "NPM not found"
fi

# PIP 패키지 설치 (버전 체크 포함)
if command -v python3 >/dev/null; then
  _info "Installing/updating PIP packages..."
  _install_pip_package "toast-cli"
else
  _skip "Python3 not found"
fi

# Step 7: OS별 시스템 설정
_progress "Configuring OS-specific settings..."

# macOS 설정
if [ "${OS_NAME}" == "darwin" ]; then
  command -v xcode-select >/dev/null || HAS_XCODE=false
  if [ ! -z "${HAS_XCODE}" ]; then
    _run "Installing Xcode Command Line Tools..."
    sudo xcodebuild -license
    xcode-select --install
    _ok "Xcode Command Line Tools installed"

    if [ "${OS_ARCH}" == "arm64" ]; then
      _run "Installing Rosetta 2 for x86_64 compatibility..."
      sudo softwareupdate --install-rosetta --agree-to-license
      _ok "Rosetta 2 installed"
    fi
  else
    _skip "Xcode Command Line Tools already installed"
  fi

  # ₩ -> ` 키 바인딩 설정
  if [ ! -f ~/Library/KeyBindings/DefaultkeyBinding.dict ]; then
    _download Library/KeyBindings/DefaultkeyBinding.dict mac/DefaultkeyBinding.dict
    _ok "Korean keyboard won symbol (₩) mapped to backtick (\`)"
  else
    _skip "Keyboard binding already configured"
  fi

  # macOS 시스템 설정
  _download .macos macos
  if [ ! -f ~/.macos.backup ]; then
    _run "Applying macOS system preferences..."
    /bin/bash ~/.macos
    _backup ~/.macos
    _ok "macOS system preferences applied"
  else
    if [ "$(_md5 ~/.dotfiles/macos)" != "$(_md5 ~/.macos.backup)" ]; then
      _run "Updating macOS system preferences..."
      /bin/bash ~/.macos
      _backup ~/.macos
      _ok "macOS system preferences updated"
    else
      _skip "macOS system preferences already applied"
    fi
  fi
fi

# Step 8: 셸 환경 설정
_progress "Installing ZSH and Oh My ZSH..."

# Oh My ZSH 설치
if [ ! -d ~/.oh-my-zsh ]; then
  _run "Installing Oh My ZSH..."
  RUNZSH=no CHSH=no /bin/bash -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" >/dev/null 2>&1
  _ok "Oh My ZSH installed"
else
  _skip "Oh My ZSH already installed"
fi

# 기본 셸을 ZSH로 변경 (oh-my-zsh 설치 여부와 별개로 체크)
if [[ "${SHELL}" != *"zsh"* ]]; then
  ZSH_PATH=$(command -v zsh)
  if [ -n "$ZSH_PATH" ]; then
    _run "Changing default shell to ZSH ($ZSH_PATH)..."

    # /etc/shells에 zsh가 등록되어 있는지 확인
    if ! grep -q "^${ZSH_PATH}$" /etc/shells 2>/dev/null; then
      echo "$ZSH_PATH" | sudo tee -a /etc/shells >/dev/null
    fi

    # chsh 실행 (권한 필요시 sudo 사용)
    if chsh -s "$ZSH_PATH" 2>/dev/null; then
      _ok "Default shell changed to ZSH"
    else
      sudo chsh -s "$ZSH_PATH" "$USER"
      _ok "Default shell changed to ZSH (with sudo)"
    fi
  else
    _error "ZSH not found in PATH"
  fi
else
  _skip "Default shell is already ZSH"
fi

# Step 9: 테마 및 UI 설정
_progress "Installing theme and UI settings..."

# Dracula 테마 디렉토리 생성
if [ ! -d ~/.dracula ]; then
  mkdir -p ~/.dracula
fi

# Dracula ZSH 테마 설치
if [ ! -d ~/.dracula/zsh ]; then
  _run "Installing Dracula theme for ZSH..."
  if git clone https://github.com/dracula/zsh.git ~/.dracula/zsh 2>/dev/null; then
    _ok "Dracula ZSH theme installed"
  else
    _warn "Failed to clone Dracula ZSH theme (network issue?)"
  fi
else
  _skip "Dracula ZSH theme already installed"
fi

# oh-my-zsh 테마 디렉토리에 링크 생성
if [ -d ~/.oh-my-zsh/themes ] && [ -d ~/.dracula/zsh ]; then
  if [ ! -L ~/.oh-my-zsh/themes/dracula.zsh-theme ]; then
    ln -sf ~/.dracula/zsh/dracula.zsh-theme ~/.oh-my-zsh/themes/dracula.zsh-theme
    _ok "Dracula theme linked to Oh My ZSH"
  else
    _skip "Dracula theme already linked"
  fi
elif [ ! -d ~/.oh-my-zsh/themes ]; then
  _skip "Oh My ZSH not found"
fi

# macOS 전용: iTerm2 Dracula 테마
if [ "${OS_NAME}" == "darwin" ]; then
  if [ ! -d ~/.dracula/iterm ]; then
    _run "Installing Dracula theme for iTerm2..."
    if git clone https://github.com/dracula/iterm.git ~/.dracula/iterm 2>/dev/null; then
      mkdir -p ~/Library/Application\ Support/iTerm2
      ln -sf ~/.dracula/iterm/Dracula.itermcolors ~/Library/Application\ Support/iTerm2/Dracula.itermcolors
      _ok "Dracula iTerm2 theme installed"
    else
      _warn "Failed to clone Dracula iTerm2 theme (network issue?)"
    fi
  else
    _skip "Dracula iTerm2 theme already installed"
  fi
fi

if [ "${OS_NAME}" == "darwin" ]; then
  # iTerm2 설정 파일
  _download .iterm2/profiles.json iterm2/profiles.json
fi

# Step 10: 사용자 설정 파일 적용
_progress "Applying user configuration files..."

# 셸 설정 파일들
_run "Downloading shell configuration files..."
_download .bashrc bashrc
_download .profile profile
_download .aliases aliases
_download .vimrc vimrc
_download .zshrc zshrc
_download .zprofile $OS_NAME/zprofile.$OS_ARCH.sh
_ok "Shell configuration files applied"

# Claude AI 설정 (~/.claude/ 디렉토리 동기화)
if [ -d ~/.dotfiles/claude ]; then
  mkdir -p ~/.claude
  cp -r ~/.dotfiles/claude/* ~/.claude/
  _ok "Claude Code settings synced to ~/.claude/"
else
  _skip "Claude Code settings not found"
fi

# Success
_success
