#!/bin/bash

# Wrap entire script in a block so the shell reads it fully into memory
# before execution. This prevents corruption when `git pull` updates this
# file while it is still running.
{

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
  INSTALLER="winget"
fi

# 설치 진행 단계 설정
TOTAL_STEPS=11
CURRENT_STEP=0

# 경고 카운터 (최종 요약에 사용)
WARN_COUNT=0

# 타이머 설정
UPDATE_INTERVAL=21600  # 6시간 (초 단위)

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
# 주의: 서브셸($(...)·파이프)에서 호출하면 카운트가 유실됨 — 루프는 `< <(...)` 패턴 유지
_warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
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
  if [ "${WARN_COUNT}" -gt 0 ]; then
    _echo "\n  ⚠ Completed with ${WARN_COUNT} warning(s) — review the ⚠ lines above." 3
  fi
  _echo
  exit 0
}

# 재시도 헬퍼 함수 (exponential backoff)
_retry() {
  local description="$1"
  shift
  local max_retries=3 retry_count=0 wait_time=5

  while [ $retry_count -lt $max_retries ]; do
    if "$@" 2>/dev/null; then return 0; fi
    retry_count=$((retry_count + 1))
    if [ $retry_count -eq $max_retries ]; then return 1; fi
    _info "$description failed, retrying in $wait_time seconds... (attempt $retry_count/$max_retries)"
    sleep $wait_time
    wait_time=$((wait_time * 2))
  done
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
    _info "Created backup: $1.backup"
  fi
}

# 파일 다운로드 함수
_download() {
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
    if ! _retry "Download ${2:-$1}" curl -fsSL --connect-timeout 10 -o ~/$1 https://raw.githubusercontent.com/nalbam/dotfiles/main/${2:-$1}; then
      _error "Failed to download ${2:-$1} after 3 attempts"
    fi
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
  if ! command -v git >/dev/null 2>&1; then
    _skip "git not found — skipping repository sync"
    return
  fi

  # macOS: CLT 미설치 상태의 git 스텁은 실행만 해도 GUI 팝업을 띄우므로 실행 전 차단
  if [ "${OS_NAME}" == "darwin" ] && ! xcode-select -p >/dev/null 2>&1; then
    _skip "Xcode CLT not installed — skipping repository sync (complete CLT install, then re-run)"
    return
  fi

  if [ ! -d ~/.dotfiles ]; then
    _run "Cloning dotfiles repository..."
    if _retry "Clone" git clone https://github.com/nalbam/dotfiles.git ~/.dotfiles; then
      _ok "Dotfiles repository cloned"
    else
      _error "Failed to clone dotfiles repository after 3 attempts"
    fi
  else
    # git -C 로 cwd 를 바꾸지 않는다 — cd/cd - 는 OLDPWD 에 의존해 실패 경로가 취약하다
    _run "Updating dotfiles repository..."
    if _retry "Pull" git -C ~/.dotfiles pull; then
      _ok "Dotfiles repository updated"
    else
      # 이미 클론이 있으므로 치명적이지 않다. 로컬 변경·네트워크 문제로 pull 이 막혀도
      # 기존 체크아웃으로 나머지 단계를 계속 진행한다 (중단하면 재실행도 같은 지점에서 막힌다).
      _warn "Failed to update dotfiles repository — continuing with existing checkout"
    fi
  fi
}

# AI settings are validated and deployed as one operation; failures stop installation.
_sync_vibe() {
  if ! command -v python3 >/dev/null 2>&1; then
    _error "AI sync requires Python 3.11 or newer."
  fi
  if ! python3 "${HOME}/.dotfiles/scripts/sync-ai-tools.py"; then
    _error "AI tools sync failed — review the error above before retrying."
  fi
}

# NPM 패키지 설치 함수 (버전 체크 포함)
# NPM_CMD is set once before calling this function (see Step 6)
_install_npm_package() {
  local package_name="$1"
  local package_spec="$2"
  local npm_cmd="${NPM_CMD:-npm}"

  # npm 실행 가능 여부 확인 (node 미설치 시 npm 호출이 exit 127 반환)
  if ! npm --version >/dev/null 2>&1; then
    _warn "npm is not functional (is node installed?), skipping $package_name"
    return 1
  fi

  # Check if package is installed
  if npm list -g "$package_spec" >/dev/null 2>&1; then
    local installed_version=$(npm list -g "$package_spec" --depth=0 2>/dev/null | grep "$package_name" | sed 's/.*@\([0-9.]*\).*/\1/')
    local latest_version=$(npm view "$package_spec" version 2>/dev/null)

    if [ -n "$installed_version" ] && [ -n "$latest_version" ]; then
      if [ "$installed_version" != "$latest_version" ]; then
        _run "Updating $package_name: $installed_version → $latest_version"
        if $npm_cmd update -g "$package_spec" >/dev/null 2>&1; then
          _ok "$package_name updated to $latest_version"
        else
          _warn "Failed to update $package_name"
        fi
      else
        _skip "$package_name already up to date ($installed_version)"
      fi
    else
      _run "Installing $package_name..."
      if $npm_cmd install -g "$package_spec" >/dev/null 2>&1; then
        _ok "$package_name installed"
      else
        _warn "Failed to install $package_name"
      fi
    fi
  else
    _run "Installing $package_name..."
    if $npm_cmd install -g "$package_spec" >/dev/null 2>&1; then
      _ok "$package_name installed"
    else
      _warn "Failed to install $package_name"
    fi
  fi
}

# pip install/upgrade를 4단계 fallback으로 시도
_pip_try_install() {
  local package_name="$1"
  shift
  local flags="$@"

  python3 -m pip install $flags "$package_name" 2>/dev/null >/dev/null ||
  python3 -m pip install --user $flags "$package_name" 2>/dev/null >/dev/null ||
  python3 -m pip install --break-system-packages --user $flags "$package_name" 2>/dev/null >/dev/null ||
  sudo python3 -m pip install $flags "$package_name" 2>/dev/null >/dev/null
}

# PIP 패키지 설치 함수 (버전 체크 포함)
_install_pip_package() {
  local package_name="$1"

  # Python3 체크
  if ! command -v python3 >/dev/null 2>&1; then
    _skip "Python3 not found, skipping $package_name"
    return 1
  fi

  # Check if package is installed
  if python3 -m pip show "$package_name" >/dev/null 2>&1; then
    local installed_version=$(python3 -m pip show "$package_name" 2>/dev/null | grep "Version:" | awk '{print $2}')
    local latest_version=$(python3 -m pip index versions "$package_name" 2>/dev/null | grep "LATEST:" | awk '{print $2}')

    if [ -n "$installed_version" ] && [ -n "$latest_version" ]; then
      if [ "$installed_version" != "$latest_version" ]; then
        _run "Updating $package_name: $installed_version → $latest_version"
        if _pip_try_install "$package_name" --upgrade; then
          _ok "$package_name updated to $latest_version"
        else
          _warn "Failed to update $package_name after trying all methods"
        fi
      else
        _skip "$package_name already up to date ($installed_version)"
      fi
    else
      _run "Installing $package_name..."
      if _pip_try_install "$package_name"; then
        _ok "$package_name installed"
      else
        _warn "Failed to install $package_name after trying all methods"
      fi
    fi
  else
    _run "Installing $package_name..."
    if _pip_try_install "$package_name"; then
      local new_version=$(python3 -m pip show "$package_name" 2>/dev/null | grep "Version:" | awk '{print $2}')
      if [ -n "$new_version" ]; then
        _ok "$package_name installed (v$new_version)"
      else
        _ok "$package_name installed"
      fi
    else
      _warn "Failed to install $package_name after trying all methods"
    fi
  fi
}

# 업데이트 타이머 체크 함수 (UPDATE_INTERVAL 간격)
_should_update() {
  local timestamp_file="$1"
  if [ ! -f "$timestamp_file" ]; then return 0; fi

  local last
  last=$(cat "$timestamp_file" 2>/dev/null)

  # 빈 파일·비숫자는 "갱신 필요"로 처리한다. 중단된 쓰기나 디스크 풀로 파일이 비면
  # $(( now - )) 가 산술 오류를 내고, 그 결과가 "갱신 불필요"로 해석되어 해당 업데이트
  # 경로가 영구히 차단된다.
  case "$last" in
    '' | *[!0-9]*) return 0 ;;
  esac

  [ $(( $(date +%s) - last )) -ge $UPDATE_INTERVAL ]
}

################################################################################
# 실행 영역 (Execution Section)
################################################################################

# 시작 배너 출력
_banner

# Parse arguments
VIBE_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --vibe) VIBE_ONLY=true ;;
  esac
done

if [ "$VIBE_ONLY" = true ]; then
  _info "Running AI tools sync only..."
  if [ -d ~/.dotfiles ]; then
    _sync_vibe
    if [ "${WARN_COUNT}" -gt 0 ]; then
      _echo "\n  ⚠ Sync completed with ${WARN_COUNT} warning(s) — review the ⚠ lines above." 3
    fi
    _echo "\n  ✓ AI tools sync complete\n" 2
    exit 0
  else
    _error "Dotfiles not installed. Run full install first."
  fi
fi

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
mkdir -p ~/.toast
# ~/.ssh 는 700 이어야 한다 — umask 에 따라 755 로 생성되면 ssh 가 config·키를 거부하거나
# 다른 사용자에게 노출된다. 기존 디렉토리도 매 실행마다 교정한다 (멱등).
chmod 700 ~/.ssh
_ok "Directories created"

# Generate SSH keys
if [ ! -f ~/.ssh/id_rsa ]; then
  if ssh-keygen -q -f ~/.ssh/id_rsa -N ''; then
    _ok "Generated RSA SSH key (~/.ssh/id_rsa)"
  else
    _warn "Failed to generate RSA SSH key"
  fi
else
  _skip "RSA SSH key already exists"
fi

if [ ! -f ~/.ssh/id_ed25519 ]; then
  if ssh-keygen -q -t ed25519 -f ~/.ssh/id_ed25519 -N ''; then
    _ok "Generated ED25519 SSH key (~/.ssh/id_ed25519)"
  else
    _warn "Failed to generate ED25519 SSH key"
  fi
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
  _info "To use 1Password: op read op://keys/ssh-config/notesPlain > ~/.ssh/config && chmod 600 ~/.ssh/config"
else
  _skip "SSH config already exists"
fi

# AWS 설정 파일 다운로드
if [ ! -f ~/.aws/config ]; then
  _download .aws/config aws/config
  _ok "Downloaded AWS config template"
  _info "To use 1Password for AWS:"
  _info "  op read op://keys/aws-config/notesPlain > ~/.aws/config && chmod 600 ~/.aws/config"
  _info "  op read op://keys/aws-credentials/notesPlain > ~/.aws/credentials && chmod 600 ~/.aws/credentials"
else
  _skip "AWS config already exists"
fi

# Git 설정 파일 다운로드
_download .gitconfig gitconfig
_download .gitconfig-bruce gitconfig-bruce
_download .gitconfig-nalbam gitconfig-nalbam
_download .gitconfig-yujh404 gitconfig-yujh404
_ok "Git configuration files downloaded"

# Step 5: OS별 패키지 관리자 설정
_progress "Setting up package managers..."

# Linux 설정 (APT 패키지 관리)
if [ "${OS_NAME}" == "linux" ]; then
  APT_TIMESTAMP_FILE=~/.toast/last_update_apt

  if _should_update "$APT_TIMESTAMP_FILE"; then
    _run "Updating APT packages..."
    # 성공 시에만 timestamp 갱신 (실패 시 다음 실행에서 재시도)
    if sudo apt update && sudo apt upgrade -y; then
      _ok "APT packages updated"
      date +%s > "$APT_TIMESTAMP_FILE"
    else
      _warn "APT update failed — will retry on next run"
    fi
  else
    _skip "APT update (last update was less than 6 hours ago)"
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
if ! command -v brew >/dev/null 2>&1; then
  _run "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
  # 사후 검증: 설치 실패를 성공으로 보고하지 않는다
  if command -v brew >/dev/null 2>&1; then
    _ok "Homebrew installed"
  else
    _warn "Homebrew install failed — continuing without brew"
  fi
else
  _skip "Homebrew already installed"
fi

# 신규 macOS 대응: Step 3 시점에는 Xcode CLT 가 없어 _dotfiles 가 git 사용을 차단하고 클론을
# 건너뛴다. 그 상태로 진행하면 Step 6 은 Brewfile 을 못 찾고 Step 11 은 sync 를 통째로 건너뛰어,
# 첫 실행이 "설정 파일만 받고 끝나는" 반쪽 설치가 된다.
# Homebrew 설치가 CLT 를 함께 넣으므로 여기서 한 번 더 시도한다. _dotfiles 는 멱등이다.
if [ ! -d ~/.dotfiles ]; then
  _info "Dotfiles repository still missing — retrying now that build tools are available"
  _dotfiles
fi

# Step 6: 개발 도구 패키지 설치
_progress "Installing development packages..."

# Homebrew 패키지 업데이트 (brew가 설치된 경우에만)
if command -v brew >/dev/null 2>&1; then
  BREW_TIMESTAMP_FILE=~/.toast/last_update_brew
  BREWFILE_SRC=~/.dotfiles/$OS_NAME/Brewfile

  # Brewfile 변경 감지: ~/.Brewfile 은 "마지막으로 bundle 성공한 내용" 마커
  BREWFILE_CHANGED=false
  if [ -f "$BREWFILE_SRC" ]; then
    if [ ! -f ~/.Brewfile ] || [ "$(_md5 "$BREWFILE_SRC")" != "$(_md5 ~/.Brewfile)" ]; then
      BREWFILE_CHANGED=true
    fi
  fi

  BREW_DUE=false
  if _should_update "$BREW_TIMESTAMP_FILE"; then BREW_DUE=true; fi

  BREW_OK=true
  if [ "$BREW_DUE" = true ]; then
    _run "Updating Homebrew packages..."
    if brew update && brew upgrade; then
      _ok "Homebrew packages updated"
    else
      _warn "brew update/upgrade failed"
      BREW_OK=false
    fi
  else
    _skip "Homebrew update (last update was less than 6 hours ago)"
  fi

  # Brewfile 설치: 스로틀 만료 또는 Brewfile 변경 시 (변경은 스로틀과 무관하게 즉시 반영)
  if [ -f "$BREWFILE_SRC" ]; then
    if [ "$BREW_DUE" = true ] || [ "$BREWFILE_CHANGED" = true ]; then
      _run "Installing packages from Brewfile..."
      if brew bundle --file="$BREWFILE_SRC"; then
        brew cleanup
        _ok "Brewfile packages installed"
        # 성공 후에만 마커 동기화 → 실패 시 다음 실행에서 CHANGED 로 재시도
        _download .Brewfile $OS_NAME/Brewfile
      else
        brew cleanup
        _warn "brew bundle failed — some packages did not install"
        BREW_OK=false
      fi
    fi
  else
    _skip "Brewfile not found for $OS_NAME"
  fi

  # 모든 단계 성공 시에만 timestamp 갱신 (실패 시 다음 실행에서 재시도)
  if [ "$BREW_DUE" = true ] && [ "$BREW_OK" = true ]; then
    date +%s > "$BREW_TIMESTAMP_FILE"
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

# nvm 부트스트랩
# brew 의 nvm formula 는 ~/.nvm 을 만들지 않고 node 도 딸려오지 않는다 (brew deps nvm 이 비어 있음).
# zshrc 는 ~/.nvm 존재를 조건으로 nvm 을 로드하므로, 여기서 만들어주지 않으면 신규 머신에서
# node/npm 이 영원히 없고 아래 NPM 패키지 설치가 통째로 skip 된다.
# 업데이트 스로틀 바깥에 둔다 — 부트스트랩은 1회성이고 Node.js 24 설치 여부로 가드된다.
NVM_SH="$(brew --prefix nvm 2>/dev/null)/nvm.sh"
if [ -s "$NVM_SH" ]; then
  export NVM_DIR="$HOME/.nvm"
  [ -d "$NVM_DIR" ] || mkdir -p "$NVM_DIR"
  . "$NVM_SH"

  if [ "$(nvm version 24)" = "N/A" ]; then
    # stderr 는 가리지 않는다 — 프리빌트 바이너리가 없는 아키텍처(예: armv7l)에서는 nvm 이
    # 소스 컴파일로 넘어가 수 시간이 걸릴 수 있고, 조용히 멈춘 것처럼 보이면 안 된다.
    _run "Installing Node.js 24 via nvm (this may take a while on ARM)"
    nvm install 24 >/dev/null || _warn "nvm install 24 failed"
  fi

  if [ "$(nvm version 24)" != "N/A" ]; then
    if nvm alias default 24 >/dev/null 2>&1 && nvm use default >/dev/null 2>&1; then
      _ok "Node.js $(node -v) configured as default"
    else
      _warn "Failed to configure Node.js 24 as default"
    fi
  fi
fi

# NPM 패키지 설치 (버전 체크 포함)
if command -v npm >/dev/null; then
  NPM_TIMESTAMP_FILE=~/.toast/last_update_npm

  if _should_update "$NPM_TIMESTAMP_FILE"; then
    _info "Installing/updating NPM packages..."

    # npm prefix 의 쓰기 권한 확인
    # sudo npm 은 lib/node_modules 에 root 소유 파일을 남겨 이후의 npm install 을
    # 영구 EACCES 로 망가뜨린다 (자가 강화 권한 오염 사이클).
    # 권한이 깨졌으면 도망가지 말고 멈춘다.
    NPM_PREFIX=$(npm config get prefix 2>/dev/null || echo "/usr/local")
    NPM_CMD="npm"
    NPM_OK=true
    NPM_NODE_MODULES="$NPM_PREFIX/lib/node_modules"

    # 컨테이너 디렉토리 자체의 쓰기 권한
    if [ -d "$NPM_NODE_MODULES" ] && [ ! -w "$NPM_NODE_MODULES" ]; then
      _warn "$NPM_NODE_MODULES is not user-writable."
      NPM_OK=false
    fi

    # 컨테이너는 user 소유여도 그 안의 패키지가 root 소유인 케이스 (과거 sudo npm 의 후유증)
    if [ "$NPM_OK" = true ] && [ -d "$NPM_NODE_MODULES" ]; then
      while IFS= read -r pkg_dir; do
        if [ ! -w "$pkg_dir" ]; then
          _warn "$pkg_dir is not user-writable (root-owned from past sudo npm)."
          NPM_OK=false
          break
        fi
      done < <(find "$NPM_NODE_MODULES" -mindepth 1 -maxdepth 1 -type d 2>/dev/null)
    fi

    if [ "$NPM_OK" = false ]; then
      _info "Do NOT use sudo npm — it permanently corrupts the node install."
      _info "Fix with: sudo chown -R \$(whoami):staff $NPM_NODE_MODULES"
      _info "Skipping NPM package install/update."
    fi

    # if [ "$NPM_OK" = true ]; then
    #   # npm 자체는 nvm 의 node 가 관리하므로 self-update 시도하지 않음
    #   _install_npm_package "corepack" "corepack"
    #   _install_npm_package "serverless" "serverless"
    #   _install_npm_package "ccusage" "ccusage"
    #   date +%s > "$NPM_TIMESTAMP_FILE"
    # fi
  else
    _skip "NPM packages update (last update was less than 6 hours ago)"
  fi
else
  _skip "NPM not found"
fi

# Claude Code 업데이트
if command -v claude >/dev/null; then
  CLAUDE_TIMESTAMP_FILE=~/.toast/last_update_claude

  if _should_update "$CLAUDE_TIMESTAMP_FILE"; then
    _run "Updating Claude Code..."
    if claude update; then
      _ok "Claude Code update completed"
      date +%s > "$CLAUDE_TIMESTAMP_FILE"
    else
      _warn "Claude Code update failed — will retry on next run"
    fi
  else
    _skip "Claude Code update (last update was less than 6 hours ago)"
  fi
else
  _skip "Claude Code not found"
fi

# PIP 패키지 설치 (버전 체크 포함)
if command -v python3 >/dev/null; then
  PIP_TIMESTAMP_FILE=~/.toast/last_update_pip

  if _should_update "$PIP_TIMESTAMP_FILE"; then
    _info "Installing/updating PIP packages..."

    # 먼저 기본 도구들을 업데이트 (setuptools, wheel 등)
    _run "Ensuring pip, setuptools, and wheel are up to date..."
    if python3 -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || \
       python3 -m pip install --user --upgrade pip setuptools wheel >/dev/null 2>&1 || \
       python3 -m pip install --break-system-packages --user --upgrade pip setuptools wheel >/dev/null 2>&1; then
      _ok "pip, setuptools, and wheel updated"
    else
      _warn "Failed to update pip tools, continuing anyway..."
    fi

    # 사용자 패키지 설치
    _install_pip_package "toast-cli"

    # Update timestamp
    date +%s > "$PIP_TIMESTAMP_FILE"
  else
    _skip "PIP packages update (last update was less than 6 hours ago)"
  fi
else
  _skip "Python3 not found"
fi

# Step 7: OS별 시스템 설정
_progress "Configuring OS-specific settings..."

# macOS 설정
if [ "${OS_NAME}" == "darwin" ]; then
  # CLT 설치 여부는 xcode-select -p 로 확인 (xcode-select 바이너리는 macOS 기본 탑재)
  if ! xcode-select -p >/dev/null 2>&1; then
    _run "Installing Xcode Command Line Tools..."
    xcode-select --install
    _warn "Xcode CLT installer launched — complete the dialog, then re-run this script"
  else
    _skip "Xcode Command Line Tools already installed"
  fi

  # Rosetta 2 는 CLT 와 독립적으로 확인 (arm64 전용, oahd 데몬으로 설치 감지)
  if [ "${OS_ARCH}" == "arm64" ]; then
    if ! pgrep -q oahd; then
      _run "Installing Rosetta 2 for x86_64 compatibility..."
      if sudo softwareupdate --install-rosetta --agree-to-license; then
        _ok "Rosetta 2 installed"
      else
        _warn "Rosetta 2 install failed"
      fi
    else
      _skip "Rosetta 2 already installed"
    fi
  fi

  # ₩ -> ` 키 바인딩 설정
  if [ ! -f ~/Library/KeyBindings/DefaultkeyBinding.dict ]; then
    _download Library/KeyBindings/DefaultkeyBinding.dict darwin/DefaultkeyBinding.dict
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
    if [ -f ~/.dotfiles/macos ] && [ "$(_md5 ~/.dotfiles/macos)" != "$(_md5 ~/.macos.backup)" ]; then
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
  RUNZSH=no CHSH=no /bin/bash -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" >/dev/null 2>&1 || true
  # 사후 검증: 설치 실패를 성공으로 보고하지 않는다
  if [ -d ~/.oh-my-zsh ]; then
    _ok "Oh My ZSH installed"
  else
    _warn "Oh My ZSH install failed (network issue?)"
  fi
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
    elif sudo chsh -s "$ZSH_PATH" "$USER"; then
      _ok "Default shell changed to ZSH (with sudo)"
    else
      _warn "Failed to change default shell to ZSH"
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
  if _retry "Dracula ZSH theme clone" git clone https://github.com/dracula/zsh.git ~/.dracula/zsh; then
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
    if _retry "Dracula iTerm2 theme clone" git clone https://github.com/dracula/iterm.git ~/.dracula/iterm; then
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

  # Ghostty 설정 파일
  _download .config/ghostty/config ghostty/config
fi

# Step 10: 사용자 설정 파일 적용
_progress "Applying user configuration files..."

# 셸 설정 파일들
_run "Downloading shell configuration files..."
_download .bashrc bashrc
_download .profile profile
_download .aliases aliases
_download .vimrc vimrc
_download .tmux.conf tmux.conf
_download .zshrc zshrc
_download .zprofile $OS_NAME/zprofile.$OS_ARCH.sh
_ok "Shell configuration files applied"

# Step 11: AI 도구 설정 (Claude Code, Codex, Kiro)
_progress "Setting up AI tools (Claude Code, Codex, Kiro)..."
_sync_vibe

# Success
_success

exit
}
