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

HOSTNAME="$(hostname)"
ORG="$(echo ${HOSTNAME} | cut -d'-' -f1)"

# 설치 진행 단계 설정
TOTAL_STEPS=10
CURRENT_STEP=0

# 타이머 설정
SECONDS_IN_DAY=86400

# 컬러 출력 설정
command -v tput >/dev/null && TPUT=true

################################################################################
# 함수 영역 (Function Section)
################################################################################

# 진행률 표시 함수
_progress() {
  CURRENT_STEP=$((CURRENT_STEP + 1))
  _echo "[$CURRENT_STEP/$TOTAL_STEPS] $@" 6
}

# 컬러 출력 함수
_echo() {
  if [ "${TPUT}" != "" ] && [ "$2" != "" ]; then
    echo -e "$(tput setaf $2)$1$(tput sgr0)"
  else
    echo -e "$1"
  fi
}

# 사용자 입력 함수
_read() {
  if [ "${TPUT}" != "" ]; then
    printf "$(tput setaf 6)$1$(tput sgr0)"
  else
    printf "$1"
  fi
  read ANSWER
}

# 결과 출력 함수
_result() {
  _echo "# $@" 4
}

# 명령어 출력 함수
_command() {
  _echo "$ $@" 3
}

# 성공 메시지 출력 함수
_success() {
  _echo "+ $@" 2
  exit 0
}

# 에러 메시지 출력 함수
_error() {
  _echo "- $@" 1
  exit 1
}

# Git 설정 함수
_git_config() {
  DEFAULT="$(whoami)"
  _read "Please input git user name [${DEFAULT}]: "

  GIT_USERNAME="${ANSWER:-${DEFAULT}}"
  git config --global user.name "${GIT_USERNAME}"

  if [ "${ORG}" == "nalbam" ]; then
    DEFAULT="me@nalbam.com"
  elif [ "${ORG}" == "Karrot" ] || [ "${ORG}" == "daangn" ]; then
    DEFAULT="${GIT_USERNAME}@daangn.com"
  else
    DEFAULT="${GIT_USERNAME}@gmail.com"
  fi
  _read "Please input git user email [${DEFAULT}]: "

  GIT_USEREMAIL="${ANSWER:-${DEFAULT}}"
  git config --global user.email "${GIT_USEREMAIL}"

  _command "git config --list"
  git config --list
}

# 백업 생성 함수
_backup() {
  if [ -f "$1" ]; then
    if ! cp "$1" "$1.backup"; then
      _error "Failed to create backup of $1"
      return 1
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

  if [ -f ~/.dotfiles/${2:-$1} ]; then
    if [ -f ~/$1 ]; then
      if [ "$(md5sum ~/.dotfiles/${2:-$1} | awk '{print $1}')" != "$(md5sum ~/$1 | awk '{print $1}')" ]; then
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
  if [ -z ${HAS_GIT} ]; then
    local max_retries=3
    local retry_count=0
    local wait_time=5

    if [ ! -d ~/.dotfiles ]; then
      _command "git clone .dotfiles"
      while [ $retry_count -lt $max_retries ]; do
        if git clone https://github.com/nalbam/dotfiles.git ~/.dotfiles; then
          break
        else
          retry_count=$((retry_count + 1))
          if [ $retry_count -eq $max_retries ]; then
            _error "Failed to clone dotfiles repository after $max_retries attempts"
          fi
          _echo "Clone failed, retrying in $wait_time seconds..." 3
          sleep $wait_time
          wait_time=$((wait_time * 2))
        fi
      done
    else
      cd ~/.dotfiles || _error "Failed to change directory to ~/.dotfiles"
      _command "git pull .dotfiles"
      while [ $retry_count -lt $max_retries ]; do
        if git pull; then
          break
        else
          retry_count=$((retry_count + 1))
          if [ $retry_count -eq $max_retries ]; then
            cd - || _error "Failed to return to previous directory"
            _error "Failed to update dotfiles repository after $max_retries attempts"
          fi
          _echo "Pull failed, retrying in $wait_time seconds..." 3
          sleep $wait_time
          wait_time=$((wait_time * 2))
        fi
      done
      cd - || _error "Failed to return to previous directory"
    fi
  fi
}

# NPM 패키지 설치 함수 (버전 체크 포함)
_install_npm_package() {
  local package_name="$1"
  local package_spec="$2"

  # Check if package is installed
  if npm list -g "$package_spec" >/dev/null 2>&1; then
    local installed_version=$(npm list -g "$package_spec" --depth=0 2>/dev/null | grep "$package_name" | sed 's/.*@\([0-9.]*\).*/\1/')
    local latest_version=$(npm view "$package_spec" version 2>/dev/null)

    if [ -n "$installed_version" ] && [ -n "$latest_version" ]; then
      if [ "$installed_version" != "$latest_version" ]; then
        _command "Updating $package_name from $installed_version to $latest_version"
        npm update -g "$package_spec"
      # else
      #   _result "$package_name is already up to date ($installed_version)"
      fi
    else
      _command "Installing $package_name (version check failed)"
      npm install -g "$package_spec"
    fi
  else
    _command "Installing $package_name"
    npm install -g "$package_spec"
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

  if [ $time_diff -ge $SECONDS_IN_DAY ]; then
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

  if [ $time_diff -ge $SECONDS_IN_DAY ]; then
    return 0
  else
    return 1
  fi
}

################################################################################
# 실행 영역 (Execution Section)
################################################################################

# Step 1: 시스템 환경 확인
_progress "Checking system environment..."
_result "${OS_NAME} ${OS_ARCH} [${INSTALLER}]"

if [ "${INSTALLER}" == "" ]; then
  _error "Unsupported operating system."
fi

# Step 2: 디렉토리 생성 및 SSH 키 설정
_progress "Creating directories and setting up SSH keys..."
mkdir -p ~/.aws
mkdir -p ~/.ssh

# Generate SSH keys
[ ! -f ~/.ssh/id_rsa ] && ssh-keygen -q -f ~/.ssh/id_rsa -N ''
[ ! -f ~/.ssh/id_ed25519 ] && ssh-keygen -q -t ed25519 -f ~/.ssh/id_ed25519 -N ''

# Step 3: Dotfiles 저장소 클론
_progress "Cloning dotfiles repository..."
_dotfiles

# Step 4: 기본 설정 파일 다운로드
_progress "Setting up basic configuration files..."

# SSH 설정 파일 다운로드
if [ ! -f ~/.ssh/config ]; then
  _download .ssh/config
  chmod 600 ~/.ssh/config
fi

# AWS 설정 파일 다운로드
if [ ! -f ~/.aws/config ]; then
  _download .aws/config
  chmod 600 ~/.aws/config
fi

# Git 설정 파일 다운로드 및 설정
if [ ! -f ~/.gitconfig ]; then
  _download .gitconfig
  _download .gitconfig-bruce
  _download .gitconfig-nalbam
  _git_config
fi

# Step 5: OS별 패키지 관리자 설정
_progress "Setting up package managers..."

# Linux 설정 (APT 패키지 관리)
if [ "${OS_NAME}" == "linux" ]; then
  APT_TIMESTAMP_FILE=~/.apt_last_update

  if should_run_apt_update; then
    _command "Running daily apt updates..."
    sudo apt update
    sudo apt upgrade -y

    command -v jq >/dev/null || HAS_JQ=false
    if [ ! -z ${HAS_JQ} ]; then
      sudo apt install -y build-essential procps curl file git unzip jq zsh
    fi

    # Update timestamp
    date +%s > "$APT_TIMESTAMP_FILE"
  else
    _command "Skipping apt updates (last update was less than 24 hours ago)"
  fi
fi

# Homebrew 설치
command -v brew >/dev/null || HAS_BREW=false
if [ ! -z ${HAS_BREW} ]; then
  _command "brew install..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [ -d /opt/homebrew/bin ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -d /home/linuxbrew ]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
  else
    eval "$(brew shellenv)"
  fi
fi

# Step 6: 개발 도구 패키지 설치
_progress "Installing development packages..."

# Homebrew 패키지 업데이트
BREW_TIMESTAMP_FILE=~/.brew_last_update

if should_run_brew_update; then
  _command "Running daily brew updates..."

  brew update
  brew upgrade

  # Brewfile 기반 패키지 설치
  _download .Brewfile $OS_NAME/Brewfile
  brew bundle --file=~/.Brewfile
  brew cleanup

  # Update timestamp
  date +%s > "$BREW_TIMESTAMP_FILE"
else
  _command "Skipping brew updates (last update was less than 24 hours ago)"
fi

# getopt 설정
GETOPT=$(getopt 2>&1 | head -1 | xargs)
if [ "${GETOPT}" == "--" ]; then
  brew link --force gnu-getopt
fi

# NPM 패키지 설치 (버전 체크 포함)
_install_npm_package "claude-code" "@anthropic-ai/claude-code"
_install_npm_package "gemini-cli" "@google/gemini-cli"

# Step 7: OS별 시스템 설정
_progress "Configuring OS-specific settings..."

# macOS 설정
if [ "${OS_NAME}" == "darwin" ]; then
  command -v xcode-select >/dev/null || HAS_XCODE=false
  if [ ! -z ${HAS_XCODE} ]; then
    _command "xcode-select --install"
    sudo xcodebuild -license
    xcode-select --install

    if [ "${OS_ARCH}" == "arm64" ]; then
      sudo softwareupdate --install-rosetta --agree-to-license
    fi
  fi

  # ₩ -> ` 키 바인딩 설정
  if [ ! -f ~/Library/KeyBindings/DefaultkeyBinding.dict ]; then
    mkdir -p ~/Library/KeyBindings/
    _download Library/KeyBindings/DefaultkeyBinding.dict .mac/DefaultkeyBinding.dict
  fi

  # macOS 시스템 설정
  _download .macos
  if [ ! -f ~/.macos.backup ]; then
    /bin/bash ~/.macos
    _backup ~/.macos
  else
    if [ "$(md5sum ~/.dotfiles/.macos | awk '{print $1}')" != "$(md5sum ~/.macos.backup | awk '{print $1}')" ]; then
      /bin/bash ~/.macos
      _backup ~/.macos
    fi
  fi
fi

# Step 8: 셸 환경 설정
_progress "Installing ZSH and Oh My ZSH..."

# Oh My ZSH 설치 및 셸 변경
if [ ! -d ~/.oh-my-zsh ]; then
  # 기본 셸을 ZSH로 변경
  THIS_SHELL="$(grep $(whoami) /etc/passwd | cut -d':' -f7)"
  if [[ "${THIS_SHELL}" != "/bin/zsh" ]]; then
    chsh -s /bin/zsh
  fi

  /bin/bash -c "$(curl -fsSL https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
fi

# Step 9: 테마 및 UI 설정
_progress "Installing theme and UI settings..."

# Dracula 테마 설치
if [ ! -d ~/.dracula ]; then
  mkdir -p ~/.dracula

  git clone https://github.com/dracula/zsh.git ~/.dracula/zsh
  ln -s ~/.dracula/zsh/dracula.zsh-theme ~/.oh-my-zsh/themes/dracula.zsh-theme

  if [ "${OS_NAME}" == "darwin" ]; then
    git clone https://github.com/dracula/iterm.git ~/.dracula/iterm
    ln -s ~/.dracula/iterm/Dracula.itermcolors ~/Library/Application\ Support/iTerm2/Dracula.itermcolors
  fi
fi

# iTerm2 설정 파일
if [ ! -d ~/.iterm2 ]; then
  mkdir -p ~/.iterm2
fi
_download .iterm2/profiles.json

# Step 10: 사용자 설정 파일 적용
_progress "Applying user configuration files..."

# 셸 설정 파일들
_download .bashrc
_download .profile
_download .aliases
_download .vimrc
_download .zshrc
_download .zprofile $OS_NAME/.zprofile.$OS_ARCH.sh

# Claude AI 설정
if [ ! -d ~/.claude ]; then
  mkdir -p ~/.claude
fi
_download .claude/CLAUDE.md

_success "Installation completed successfully!"
