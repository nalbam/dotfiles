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

HOSTNAME="$(hostname)"

ORG="$(echo ${HOSTNAME} | cut -d'-' -f1)"

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

_backup() {
  if [ -f $1 ]; then
    cp $1 $1.backup
  fi
}

_download() {
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
    curl -fsSL -o ~/$1 https://raw.githubusercontent.com/nalbam/dotfiles/main/${2:-$1}
  fi
}

_dotfiles() {
  command -v git >/dev/null || HAS_GIT=false
  if [ -z ${HAS_GIT} ]; then
    if [ ! -d ~/.dotfiles ]; then
      _command "git clone .dotfiles"
      git clone https://github.com/nalbam/dotfiles.git ~/.dotfiles
    else
      cd ~/.dotfiles
      _command "git pull .dotfiles"
      git pull
      cd -
    fi
  fi
}

################################################################################

_result "${OS_NAME} ${OS_ARCH} [${INSTALLER}]"

if [ "${INSTALLER}" == "" ]; then
  _error "Not supported OS."
fi

mkdir -p ~/.aws
mkdir -p ~/.ssh

# ssh keygen
[ ! -f ~/.ssh/id_rsa ] && ssh-keygen -q -f ~/.ssh/id_rsa -N ''
[ ! -f ~/.ssh/id_ed25519 ] && ssh-keygen -q -t ed25519 -f ~/.ssh/id_ed25519 -N ''

# dotfiles
_dotfiles

# ssh config
if [ ! -f ~/.ssh/config ]; then
  _download .ssh/config
  chmod 600 ~/.ssh/config
fi

# aws config
if [ ! -f ~/.aws/config ]; then
  _download .aws/config
  chmod 600 ~/.aws/config
fi

# .gitconfig
if [ ! -f ~/.gitconfig ]; then
  _download .gitconfig
  _download .gitconfig-daangn
  _download .gitconfig-nalbam
  _git_config
fi

# brew for mac
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

  # ₩ -> `
  if [ ! -f ~/Library/KeyBindings/DefaultkeyBinding.dict ]; then
    mkdir -p ~/Library/KeyBindings/
    _download Library/KeyBindings/DefaultkeyBinding.dict .mac/DefaultkeyBinding.dict
  fi

  # .macos
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

# brew for linux
if [ "${OS_NAME}" == "linux" ]; then
  _command "apt update..."
  sudo apt update

  _command "apt upgrade..."
  sudo apt upgrade -y

  command -v jq >/dev/null || HAS_JQ=false
  if [ ! -z ${HAS_JQ} ]; then
    sudo apt install -y build-essential procps curl file git unzip jq zsh

    # sudo apt install -y make build-essential git fzf zsh file wget curl llvm procps unzip jq apt-transport-https ca-certificates \
    #                     libreadline-dev libsqlite3-dev  libncurses5-dev libncursesw5-dev libssl-dev zlib1g-dev libbz2-dev \
    #                     xz-utils tk-dev
  fi
fi

# brew
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

_command "brew update..."
brew update

_command "brew upgrade..."
brew upgrade

# Brewfile
_download .Brewfile $OS_NAME/Brewfile

_command "brew bundle..."
brew bundle --file=~/.Brewfile

_command "brew cleanup..."
brew cleanup

# # zsh
# command -v zsh >/dev/null || HAS_ZSH=false
# if [ ! -z ${HAS_ZSH} ]; then
#   _command "brew install zsh"
#   brew install zsh
# fi

# getopt
GETOPT=$(getopt 2>&1 | head -1 | xargs)
if [ "${GETOPT}" == "--" ]; then
  brew link --force gnu-getopt
fi

# oh-my-zsh
if [ ! -d ~/.oh-my-zsh ]; then
  # chsh zsh
  THIS_SHELL="$(grep $(whoami) /etc/passwd | cut -d':' -f7)"
  if [[ "${THIS_SHELL}" != "/bin/zsh" ]]; then
    chsh -s /bin/zsh
  fi

  /bin/bash -c "$(curl -fsSL https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
fi

# dracula theme
if [ ! -d ~/.dracula ]; then
  mkdir -p ~/.dracula

  git clone https://github.com/dracula/zsh.git ~/.dracula/zsh
  ln -s ~/.dracula/zsh/dracula.zsh-theme ~/.oh-my-zsh/themes/dracula.zsh-theme

  if [ "${OS_NAME}" == "darwin" ]; then
    git clone https://github.com/dracula/iterm.git ~/.dracula/iterm
    ln -s ~/.dracula/iterm/Dracula.itermcolors ~/Library/Application\ Support/iTerm2/Dracula.itermcolors
  fi
fi

# .bashrc
_download .bashrc

# .profile
_download .profile

# .aliases
_download .aliases

# .vimrc
_download .vimrc

# .zshrc
_download .zshrc

# .zprofile
_download .zprofile $OS_NAME/.zprofile.$OS_ARCH.sh

# .iterm2
if [ ! -d ~/.iterm2 ]; then
  mkdir -p ~/.iterm2
fi
_download .iterm2/profiles.json

# _command "check versions..."
# _result "awscli:  $(aws --version | cut -d' ' -f1 | cut -d'/' -f2)"
# _result "kubectl: $(kubectl version --client -o json | jq .clientVersion.gitVersion -r)"
# _result "helm:    $(helm version --client --short | cut -d'+' -f1)"
# _result "argocd:  $(argocd version --client -o json | jq .client.Version -r | cut -d'+' -f1)"

_success
