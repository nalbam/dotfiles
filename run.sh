#!/bin/bash

OS_NAME="$(uname | awk '{print tolower($0)}' | cut -d'-' -f1)"
OS_ARCH="$(uname -m)"

if [ "${OS_NAME}" == "darwin" ]; then
  INSTALLER="brew"
elif [ "${OS_NAME}" == "linux" ]; then
  INSTALLER="apt"
elif [ "${OS_NAME}" == "mingw64_nt" ]; then
  INSTALLER="choco"
fi

################################################################################

command -v tput >/dev/null && TPUT=true

_echo() {
  if [ "${TPUT}" != "" ] && [ "$2" != "" ]; then
    echo -e "$(tput setaf $2)$1$(tput sgr0)"
  else
    echo -e "$1"
  fi
}

_read() {
  if [ "${TPUT}" != "" ]; then
    printf "$(tput setaf 6)$1$(tput sgr0)"
  else
    printf "$1"
  fi
  read ANSWER
}

_result() {
  _echo "# $@" 4
}

_command() {
  _echo "$ $@" 3
}

_success() {
  _echo "+ $@" 2
  exit 0
}

_error() {
  _echo "- $@" 1
  exit 1
}

_git_config() {
  # git config --global user.name "nalbam"
  # git config --global user.email "me@nalbam.com"

  DEFAULT="$(whoami)"
  _read "Please input git user name [${DEFAULT}]: "

  GIT_USERNAME="${ANSWER:-${DEFAULT}}"
  git config --global user.name "${GIT_USERNAME}"

  DEFAULT="me@${GIT_USERNAME}.com"
  _read "Please input git user email [${DEFAULT}]: "

  GIT_USEREMAIL="${ANSWER:-${DEFAULT}}"
  git config --global user.email "${GIT_USEREMAIL}"

  _command "git config --list"
  git config --list
}

_install_brew() {
  INSTALLED=
  command -v $1 >/dev/null || INSTALLED=false
  if [ ! -z ${INSTALLED} ]; then
    _command "brew install ${2:-$1}"
    brew install ${2:-$1}
  fi
}

_install_brew_path() {
  INSTALLED=$(cat /tmp/brew_list | grep "$1" | wc -l | xargs)

  if [ "x${INSTALLED}" == "x0" ]; then
    _command "brew install ${2:-$1}"
    brew install ${2:-$1}
  fi
}

_install_brew_apps() {
  INSTALLED=$(ls /Applications/ | grep "$1" | wc -l | xargs)

  if [ "x${INSTALLED}" == "x0" ]; then
    _command "brew install -cask ${2:-$1}"
    brew install -cask ${2:-$1}
  fi
}

_install_apt() {
  INSTALLED=
  command -v $1 >/dev/null || INSTALLED=false
  if [ ! -z ${INSTALLED} ]; then
    _command "sudo apt install -y ${2:-$1}"
    apt install -y ${2:-$1}
  fi
}

_install_npm() {
  INSTALLED=
  command -v $1 >/dev/null || INSTALLED=false
  if [ ! -z ${INSTALLED} ]; then
    _command "npm install -g ${2:-$1}"
    npm install -g ${2:-$1}
  fi
}

_install_npm_path() {
  if [ -d /usr/local/lib/node_modules/ ]; then
    INSTALLED=$(ls /usr/local/lib/node_modules/ | grep "$1" | wc -l | xargs)
  else
    INSTALLED=
  fi

  if [ "x${INSTALLED}" == "x0" ]; then
    _command "npm install -g ${2:-$1}"
    npm install -g ${2:-$1}
  fi
}

_backup() {
  if [ -f $1 ] && [ ! -f $1.backup ]; then
    cp $1 $1.backup
  fi
}

_download() {
  _backup ~/$1
  curl -fsSL -o ~/$1 https://raw.githubusercontent.com/nalbam/dotfiles/main/${2:-$1}
}

################################################################################

_result "${OS_NAME} ${OS_ARCH} [${INSTALLER}]"

if [ "${INSTALLER}" == "" ]; then
  _error "Not supported OS."
fi

# sudo -v

# # Keep-alive: update existing `sudo` time stamp
# while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &

mkdir -p ~/.aws
mkdir -p ~/.ssh

# ssh keygen
[ ! -f ~/.ssh/id_rsa ] && ssh-keygen -q -f ~/.ssh/id_rsa -N ''
[ ! -f ~/.ssh/id_ed25519 ] && ssh-keygen -q -t ed25519 -f ~/.ssh/id_ed25519 -N ''

# ssh config
if [ ! -f ~/.ssh/config ]; then
  curl -fsSL -o ~/.ssh/config https://raw.githubusercontent.com/nalbam/dotfiles/main/.ssh/config
  chmod 600 ~/.ssh/config
fi

# aws config
if [ ! -f ~/.aws/config ]; then
  curl -fsSL -o ~/.aws/config https://raw.githubusercontent.com/nalbam/dotfiles/main/.aws/config
  chmod 600 ~/.aws/config
fi

# .aliases
_backup ~/.aliases
curl -fsSL -o ~/.aliases https://raw.githubusercontent.com/nalbam/dotfiles/main/.aliases

# .vimrc
_backup ~/.vimrc
curl -fsSL -o ~/.vimrc https://raw.githubusercontent.com/nalbam/dotfiles/main/.vimrc

# .gitconfig
if [ ! -f ~/.gitconfig ]; then
  curl -fsSL -o ~/.gitconfig https://raw.githubusercontent.com/nalbam/dotfiles/main/.gitconfig
  _git_config
fi

# brew for mac
if [ "${INSTALLER}" == "brew" ]; then
  command -v xcode-select >/dev/null || HAS_XCODE=false
  if [ ! -z ${HAS_XCODE} ]; then
    _command "xcode-select --install"
    sudo xcodebuild -license
    xcode-select --install

    if [ "${OS_ARCH}" == "arm64" ]; then
      sudo softwareupdate --install-rosetta --agree-to-license
    fi
  fi

  # ₩ -> `
  if [ ! -f ~/Library/KeyBindings/DefaultkeyBinding.dict ]; then
    mkdir -p ~/Library/KeyBindings/
    curl -fsSL -o ~/Library/KeyBindings/DefaultkeyBinding.dict https://raw.githubusercontent.com/nalbam/dotfiles/main/.mac/DefaultkeyBinding.dict
  fi

  # .macos
  if [ ! -f ~/.macos ]; then
    curl -fsSL -o ~/.macos https://raw.githubusercontent.com/nalbam/dotfiles/main/.macos
    /bin/bash ~/.macos
  fi

  # brew
  command -v brew >/dev/null || HAS_BREW=false
  if [ ! -z ${HAS_BREW} ]; then
    _command "brew install..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [ -d "/opt/homebrew/bin" ]; then
      eval "$(/opt/homebrew/bin/brew shellenv)"
    else
      eval "$(brew shellenv)"
    fi
  fi

  _command "brew update..."
  brew update

  _command "brew upgrade..."
  brew upgrade

  brew list >/tmp/brew_list

  # zsh
  command -v zsh >/dev/null || HAS_ZSH=false
  if [ ! -z ${HAS_ZSH} ]; then
    _command "brew install zsh"
    brew install zsh
  fi

  # getopt
  GETOPT=$(getopt 2>&1 | head -1 | xargs)
  if [ "${GETOPT}" == "--" ]; then
    _command "brew install gnu-getopt"
    brew install gnu-getopt
    brew link --force gnu-getopt
  fi

  # podman
  if [ "${OS_ARCH}" == "x86_64" ]; then
    _install_brew_path qemu
    _install_brew_path podman
  elif [ "${OS_ARCH}" == "arm64" ]; then
    _install_brew_path podman-apple-silicon simnalamburt/x/podman-apple-silicon
  fi

  # Brewfile
  if [ -f ~/.Brewfile ] && [ ! -f ~/.Brewfile.backup ]; then
    cp ~/.Brewfile ~/.Brewfile.backup
  fi
  curl -fsSL -o ~/.Brewfile https://raw.githubusercontent.com/nalbam/dotfiles/main/Brewfile

  _command "brew bundle..."
  brew bundle --file=~/.Brewfile

  _command "check versions..."
  _result "awscli:  $(aws --version | cut -d' ' -f1 | cut -d'/' -f2)"
  _result "kubectl: $(kubectl version --client -o json | jq .clientVersion.gitVersion -r)"
  _result "helm:    $(helm version --client --short | cut -d'+' -f1)"
  _result "argocd:  $(argocd version --client -o json | jq .client.Version -r | cut -d'+' -f1)"

  _command "brew cleanup..."
  brew cleanup
fi

# brew for ubuntu
if [ "${INSTALLER}" == "apt" ]; then
  _command "apt update..."
  sudo apt update

  _command "apt upgrade..."
  sudo apt upgrade -y

  command -v zsh >/dev/null || HAS_ZSH=false
  if [ ! -z ${HAS_ZSH} ]; then
    sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev git fzf zsh \
                        libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
                        xz-utils tk-dev jq
  fi

  if [ ! -d ~/.pyenv ]; then
    git clone https://github.com/pyenv/pyenv.git ~/.pyenv
  fi

  if [ ! -d ~/.tfenv ]; then
    git clone https://github.com/tfutils/tfenv.git ~/.tfenv
  fi
fi

# chsh zsh
THIS_SHELL="$(grep $(whoami) /etc/passwd | cut -d':' -f7)"
if [[ "${THIS_SHELL}" == "/bin/zsh" ]]; then
  chsh -s /bin/zsh
fi

# oh-my-zsh
if [ ! -d ~/.oh-my-zsh ]; then
  /bin/bash -c "$(curl -fsSL https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
fi

# .bashrc
_backup ~/.bashrc
curl -fsSL -o ~/.bashrc https://raw.githubusercontent.com/nalbam/dotfiles/main/.bashrc

# .profile
_backup ~/.profile
curl -fsSL -o ~/.profile https://raw.githubusercontent.com/nalbam/dotfiles/main/.profile

# .zshrc
_backup ~/.zshrc
curl -fsSL -o ~/.zshrc https://raw.githubusercontent.com/nalbam/dotfiles/main/.zshrc

# .zprofile
_backup ~/.zprofile
curl -fsSL -o ~/.zprofile https://raw.githubusercontent.com/nalbam/dotfiles/main/.zprofile.${OS_NAME}.${OS_ARCH}

_success
